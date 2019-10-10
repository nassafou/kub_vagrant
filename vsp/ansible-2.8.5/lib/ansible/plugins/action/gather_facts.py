# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import time

from ansible import constants as C
from ansible.plugins.action import ActionBase
from ansible.utils.vars import combine_vars


class ActionModule(ActionBase):

    def _get_module_args(self, fact_module, task_vars):

        mod_args = self._task.args.copy()

        # deal with 'setup specific arguments'
        if fact_module != 'setup':

            # network facts modules must support gather_subset
            if self._connection._load_name not in ('network_cli', 'httpapi', 'netconf'):
                subset = mod_args.pop('gather_subset', None)
                if subset not in ('all', ['all']):
                    self._display.warning('Ignoring subset(%s) for %s' % (subset, fact_module))

            timeout = mod_args.pop('gather_timeout', None)
            if timeout is not None:
                self._display.warning('Ignoring timeout(%s) for %s' % (timeout, fact_module))

            fact_filter = mod_args.pop('filter', None)
            if fact_filter is not None:
                self._display.warning('Ignoring filter(%s) for %s' % (fact_filter, fact_module))

        # Strip out keys with ``None`` values, effectively mimicking ``omit`` behavior
        # This ensures we don't pass a ``None`` value as an argument expecting a specific type
        mod_args = dict((k, v) for k, v in mod_args.items() if v is not None)

        return mod_args

    def run(self, tmp=None, task_vars=None):

        self._supports_check_mode = True

        result = super(ActionModule, self).run(tmp, task_vars)
        result['ansible_facts'] = {}

        modules = C.config.get_config_value('FACTS_MODULES', variables=task_vars)
        parallel = task_vars.pop('ansible_facts_parallel', self._task.args.pop('parallel', None))

        if 'smart' in modules:
            connection_map = C.config.get_config_value('CONNECTION_FACTS_MODULES', variables=task_vars)
            modules.extend([connection_map.get(self._connection._load_name, 'setup')])
            modules.pop(modules.index('smart'))

        failed = {}
        skipped = {}
        if parallel is False or (len(modules) == 1 and parallel is None):
            # serially execute each module
            for fact_module in modules:
                # just one module, no need for fancy async
                mod_args = self._get_module_args(fact_module, task_vars)
                res = self._execute_module(module_name=fact_module, module_args=mod_args, task_vars=task_vars, wrap_async=False)
                if res.get('failed', False):
                    failed[fact_module] = res
                elif res.get('skipped', False):
                    skipped[fact_module] = res
                else:
                    result = combine_vars(result, {'ansible_facts': res.get('ansible_facts', {})})

            self._remove_tmp_path(self._connection._shell.tmpdir)
        else:
            # do it async
            jobs = {}
            for fact_module in modules:

                mod_args = self._get_module_args(fact_module, task_vars)
                self._display.vvvv("Running %s" % fact_module)
                jobs[fact_module] = (self._execute_module(module_name=fact_module, module_args=mod_args, task_vars=task_vars, wrap_async=True))

            while jobs:
                for module in jobs:
                    poll_args = {'jid': jobs[module]['ansible_job_id'], '_async_dir': os.path.dirname(jobs[module]['results_file'])}
                    res = self._execute_module(module_name='async_status', module_args=poll_args, task_vars=task_vars, wrap_async=False)
                    if res.get('finished', 0) == 1:
                        if res.get('failed', False):
                            failed[module] = res
                        elif res.get('skipped', False):
                            skipped[module] = res
                        else:
                            result = combine_vars(result, {'ansible_facts': res.get('ansible_facts', {})})
                        del jobs[module]
                        break
                    else:
                        time.sleep(0.1)
                else:
                    time.sleep(0.5)

        if skipped:
            result['msg'] = "The following modules were skipped: %s\n" % (', '.join(skipped.keys()))
            result['skipped_modules'] = skipped
            if len(skipped) == len(modules):
                result['skipped'] = True

        if failed:
            result['failed'] = True
            result['msg'] = "The following modules failed to execute: %s\n" % (', '.join(failed.keys()))
            result['failed_modules'] = failed

        # tell executor facts were gathered
        result['ansible_facts']['_ansible_facts_gathered'] = True

        # hack to keep --verbose from showing all the setup module result
        result['_ansible_verbose_override'] = True

        return result
