#! python2
# -*- encoding:utf-8 -*-
"""
Name: ssh_forward
Date: 2016/3/2 0:20
Author: lniwn
E-mail: lniwn@live.com

"""

from __future__ import print_function, unicode_literals

import socket
import threading
import time
try:
    import Queue
except ImportError:
    import queue as Queue

# a list of forward mapping
forward_list = [{'local_host': ('127.0.0.1', 5280), 'forward_host': ('192.168.137.168', 1025)},
                {'local_host': ('127.0.0.1', 5281), 'forward_host': ('127.0.0.1', 8888)}]

# sync all the threads in each of tunnel
running_flag = []

# receive buffSize
buffer_size = 2048

# queue operator time
queue_timeout = 10


def get_data_from_ssh_server(rev_msg, tcp_socket, flag):
    """
    :param rev_msg: a queue buffer of message need to be send to SSH client
    :param tcp_socket: instance of socket used for sending data
    :param flag: control this function
    :return: None
    """
    while running_flag[flag]:
        data = tcp_socket.recv(buffer_size)
        if data and len(data):
            rev_msg.put(data)
        else:
            running_flag[flag] = False


def send_data_to_ssh_client(rev_msg, tcp_socket, flag):
    """
    :param rev_msg: a queue buffer of message need to be send to SSH client
    :param tcp_socket: instance of socket used for sending data
    :param flag: control this function
    :return: None
    """
    while running_flag[flag]:
        try:
            data = rev_msg.get(timeout=queue_timeout)
            tcp_socket.send(data)
        except socket.error:
            pass
        except Queue.Empty:
            pass


def get_data_from_ssh_client(send_msg, tcp_socket, flag):
    """
    :param send_msg: a queue buffer of message need to be send to SSH server in each machine
    :param tcp_socket: instance of socket used for sending data
    :param flag: control this function
    :return: None
    """
    while running_flag[flag]:
        data = tcp_socket.recv(buffer_size)
        if data and len(data):
            send_msg.put(data)
        else:
            running_flag[flag] = False


def send_data_to_ssh_server(send_msg, tcp_socket, flag):
    """
   :param send_msg: a queue buffer of message need to be send to SSH server in each machine
    :param tcp_socket: instance of socket used for sending data
    :param flag: control this function
    :return: None
    """
    while running_flag[flag]:
        try:
            data = send_msg.get(timeout=queue_timeout)
            tcp_socket.send(data)
        except socket.error:
            pass
        except Queue.Empty:
            pass


def handle_connection(local_host, forward_host):
    """
    :param local_host: local host
    :param forward_host: which machine the data will be forwarded
    :return: None
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(local_host)

    # allow 10 clients
    client_socket.listen(10)

    while True:
        ssh_client, ssh_adr = client_socket.accept()
        print(time.asctime(), '<===>', ssh_adr)

        ssh_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ssh_server.connect(forward_host)
        except socket.error:
            print('**connect to', forward_host, 'occurs an error!')
            continue

        # two queue for keeping data from SSH client and SSH server
        send_buffer = Queue.Queue()
        rev_buffer = Queue.Queue()

        running_flag.append(True)

        rev1 = threading.Thread(target=get_data_from_ssh_server,
                                args=(rev_buffer, ssh_server, len(running_flag) - 1))
        send1 = threading.Thread(target=send_data_to_ssh_client,
                                 args=(rev_buffer, ssh_client, len(running_flag) - 1))
        rev2 = threading.Thread(target=get_data_from_ssh_client,
                                args=(send_buffer, ssh_client, len(running_flag) - 1))
        send2 = threading.Thread(target=send_data_to_ssh_server,
                                 args=(send_buffer, ssh_server, len(running_flag) - 1))
        threads = (rev1, rev2, send1, send2)
        for t in threads:
            t.daemon = True
            t.start()


def main():
    print('SSH forward server is running')

    threads = []
    for i in forward_list:
        print('SSH MAPPING', i['local_host'], '<===>', i['forward_host'])
        t = threading.Thread(target=handle_connection, args=(i['local_host'], i['forward_host']))
        threads.append(t)
        t.start()

    for i in threads:
        i.join()


if __name__ == '__main__':
    main()
