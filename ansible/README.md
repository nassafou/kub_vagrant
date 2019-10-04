# Ansible tutorial

### Run playbooks for production

    Not for now
    
### Run playbooks for staging or test

* Deploy system

    ````
    ansible-playbook -i staging --user root site.yml
    ````
* Update system

    ````
    ansible-playbook -i staging --user root --tags update site.yml
    ````
* Backup system

    ````
    ansible-playbook -i staging --user root --tags backup site.yml
    ````
* Restore backup

    ````
    ansible-playbook -i staging --user root --tags restore site.yml
    ````

![Wordpress Screenshot](/wordpress-freshinstall-screenshot.jpeg)
