#-*- coding:utf8 -*- 
# @author Thierry Stiegler thierry.stiegler@gmail.com

from fabric.api import *
from fabric.colors import red,yellow,green
from fabric.contrib.console import confirm
from fabric.utils import abort,error

from pprint import pprint

import os

# SETTINGS

IMAGES = ["base","postgresql", "mysql", "http", "php", "wsgi"]

NODES = [
    { "id": 1, "name" : "prodpostgresql01"     , "image":"qqch/postgresql:latest", "extra_port":"5432%(id)s:5432"  },
    { "id": 2, "name" : "prodmysql01"          , "image":"qqch/mysql:latest"     , "extra_port":"3306%(id)s:3306"  },
    { "id": 3, "name" : "prodjibaku01"         , "image":"qqch/wsgi:latest"      , "extra_port":"800%(id)s:80"     },
    { "id": 4, "name" : "prodjeanglode01"      , "image":"qqch/wsgi:latest"      , "extra_port":"800%(id)s:80"     },
    { "id": 5, "name" : "prodjeanglode02"      , "image":"qqch/php:latest"       , "extra_port":"800%(id)s:80"   , "links":("prodmysql01:db",)  },
    { "id": 6, "name" : "prodwp01"             , "image":"qqch/php:latest"       , "extra_port":"800%(id)s:80"     },
    { "id": 7, "name" : "prodtorzka01"         , "image":"qqch/php:latest"       , "extra_port":"800%(id)s:80"     },
]

NETWORKS = [
    { "id": 1, "nodes": ("prodmysql01", "prodjeanglode02", "prodjeanglode01") },
    { "id": 2, "nodes": ("prodpostgresql01", "prodjibaku01")},
    { "id": 3, "nodes": ("prodmysql01", "prodwp01")},
    { "id": 4, "nodes": ("prodmysql01", "prodtorzka01")},

]

DOCKERFILES_ROOT = "/home/docker/dockerfiles"
CONTAINERS_DATAROOT = "/home/docker/volumes/"

DKCLEAN_CMD = "/home/docker/bin/dkclean.sh"
PIPEWORK_CMD = "sudo /home/docker/bin/pipework"
# TASKS



@task
def cluster(cmd=None):
    """
    The cluster mini wrapper, values for cmd arg : boot,start,stop,destroy
      * fab cluster:boot : do a 'docker.io run' on each container, run it once time
      * fab cluster:stop : stop all containers in the cluster
      * fab cluster:start : do a 'docker.io start' on each container
      * fab cluster:destroy : destroy all the cluster and clean docker's data (see dkclean)
    """

    generic_msg  = "\nAvailable commands are :\n  * start\n  * stop\n  * destroy\n  * boot"

    if cmd == "start":
        cluster_start()
        puts(green("cluster start [OK]"))
    elif cmd == "stop":
        cluster_stop()
        puts(green("cluster stop [OK]"))
    elif cmd == "boot":
        cluster_boot()
        puts(green("cluster boot [OK]"))
    elif cmd == "destroy":
        if confirm("Are you sure to destroy ? Everything you need is backuped ?",default=False):
            cluster_destroy()
            puts(green("cluster destroy [OK]"))
        else:
            abort(yellow("cluster destroy [CANCELED]"))
    elif cmd == None:
        puts(generic_msg)
    else:
        error(red("commande %s not found !" % cmd))
        puts(generic_msg)
 
@task
def dockerui(cmd=None):
    """
    The dockerui mini wrapper, values for cmd arg : boot,start,stop,destroy
      * fab dockerui:boot : do a 'docker.io run' on each container, run it once time
      * fab dockerui:stop : stop all containers in the dockerui
      * fab dockerui:start : do a 'docker.io start' on each container
      * fab dockerui:destroy : destroy all the dockerui and clean docker's data (see dkclean)
    """

    generic_msg  = "\nAvailable commands are :\n  * start\n  * stop\n  * destroy\n  * boot"

    if cmd == "start":
        dockerui_start()
        puts(green("dockerui start [OK]"))
    elif cmd == "stop":
        dockerui_stop()
        puts(green("dockerui stop [OK]"))
    elif cmd == "boot":
        dockerui_boot()
        puts(green("dockerui boot [OK]"))
    elif cmd == "destroy":
        if confirm("Are you sure to destroy ? Everything you need is backuped ?",default=False):
            dockerui_destroy()
            puts(green("dockerui destroy [OK]"))
        else:
            abort(yellow("dockerui destroy [CANCELED]"))
    elif cmd == None:
        puts(generic_msg)
    else:
        error(red("commande %s not found !" % cmd))
        puts(generic_msg)        

@task
def build(*images):
    """
    Build given images in args. if args is empty it builds %s
    """ % IMAGES

    if len(images) <= 0:
        images = IMAGES
  
    for image in images:
        dirname = "qqch-%s" % (image,)
        options = {
          "image":image,
          "dpath" : os.path.join(DOCKERFILES_ROOT, dirname),
         }
        local("docker.io build -t qqch/%(image)s %(dpath)s" % options)

    puts("Please run dkclean now !")


@task
def dkclean():
    """
    Fabric wrapper around the dkclean command that clean docker's garbage
    """
    local(DKCLEAN_CMD)
   

def dockerui_boot():
    local("docker.io run -h dockerui --name=dockerui -d -p 9000:9000 -v /var/run/docker.sock:/docker.sock crosbymichael/dockerui -e /docker.sock")

def dockerui_start():
    local("docker.io start dockerui")

def dockerui_stop():
    local("docker.io stop dockerui")


def dockerui_destroy():
    local("docker.io kill dockerui")
    dkclean()

def getports(defnode):
    options = {
      "convention" : "--publish=220%(id)s:22 --publish=490%(id)s:4949" ,
      "extra"      : "",
    }

    if defnode.has_key("extra_port"):
        options["extra"] = "--publish=%(extra_port)s" % defnode
    
    tpl = "%(convention)s %(extra)s" % options
    return tpl % defnode


def getvpath(defnode):
    return os.path.join(CONTAINERS_DATAROOT, defnode.get("name"))

      
def getlinks(defnode):
    r = ""
    for link in defnode.get("links", [] ):
        fragment = "--link=%s" % link
        r = r + fragment
    return r

        
def cluster_boot():
    for defnode in NODES:
        defnode["ports"] = getports(defnode)
        defnode["vpath"] = getvpath(defnode)
        defnode["linking"] = getlinks(defnode)
        local("mkdir -p %(vpath)s" % defnode)
        cmd = "docker.io run --hostname=%(name)s --name=%(name)s -v %(vpath)s:/data %(ports)s %(linking)s -d -t %(image)s  /sbin/my_init" % defnode
        local(cmd)
    network_up()

def cluster_exec(cmd):
    for defnode in NODES :
        local(cmd % defnode)  

def cluster_stop():
    cluster_exec("docker.io stop %(name)s")


def cluster_destroy():
    cluster_exec("docker.io kill %(name)s")
    dkclean()


def cluster_start():
    cluster_exec("docker.io start %(name)s")
    network_up()

def conf_render(tpl):
    for defnode in NODES:
        puts(tpl % defnode)

@task
def conf(cmd=None):
    """
    The conf mini wrapper, values for cmd arg : boot,start,stop,destroy
      * fab conf:munin : generate the node tree for /etc/munin/munin.conf
      * fab conf:upstreams : generate the upstreams definition for nginx
      * fab conf:ufw : generate the ufw rules for making ssh available from the outside for every container
    """

    generic_msg  = "\nAvailable commands are :\n  * munin\n  * ssh"

    if cmd == "ssh":
        conf_munin()
    elif cmd == "upstreams":
        conf_upstreams()
    elif cmd == "ufw":
        puts(generic_msg)
    elif cmd == None:
        puts(generic_msg)
    else:
        error(red("commande %s not found !" % cmd))
        puts(generic_msg)


def conf_munin():
    tpl = """
[docker;%(name)s]
    address 172.17.42.1
    port 490%(id)s
    use_node_name yes
"""
    conf_render(tpl)


def conf_upstreams():
    tpl ="""
upstream %(name)s {
    server 172.17.42.1:800%(id)s;
}
"""
    conf_render(tpl)

def conf_ufw():
    tpl = """
ufw allow out 220%(id)s
"""
    conf_render(tpl)


@task
def network_up():
    """
    Build privates networks between containers
    """
    for network in NETWORKS:
        options = {
            "pipework": PIPEWORK_CMD,
        } 
        print network
        for idx, node in enumerate(network.get("nodes")):
            options["node"] = node
            options["ip"] = idx+1
            options.update(network)
            cmd = "%(pipework)s br%(id)s -i eth%(id)s  %(node)s  192.168.%(id)s.%(ip)s/24" % options
            local(cmd) 


@task
def ssh(name):
     """
     Open a ssh session to qqch@{container_name}
     """
    
     found = False
     for node in NODES:
          if node.get("name") == name:
              local("ssh qqch@127.1 -p220%(id)s " % node)
              found = True
     if not found:
          puts(red("%s not found in cluster definition" % name))


@task
def ls():
    """
    List containers configuration
    """
    for node in NODES:
        puts(yellow("%s : " % node.get("name") ))
        puts("------------------------")
        pprint(node) 
        puts("------------------------\n\n")
