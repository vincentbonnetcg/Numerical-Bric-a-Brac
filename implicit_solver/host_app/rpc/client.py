"""
@author: Vincent Bonnet
@description : Client implementation to communicates with the server
"""

import functools
from multiprocessing.managers import SyncManager

class ServerQueueManager(SyncManager):
    pass

ServerQueueManager.register('get_job_queue')
ServerQueueManager.register('get_result_queue')


class ClientDispatcher:
    def __init__(self, client):
        self.client = client
        commands = self.client.run('get_commands')
        if not commands:
            return

        for command in commands:
            if hasattr(self, command):
                raise ValueError(f'in register_cmd() {command} already registered')

            func = functools.partial(self.run, command)
            setattr(self, command, func)

    def run(self, command_name, **kwargs):
        return self.client.run(command_name, **kwargs)

class Client:
    '''
    Client to connect and dispatch commands to a Server
    '''
    def __init__(self, name = "noname"):
        self._manager = None
        self._job_queue = None
        self._result_queue = None
        self._name = name # name of the client for server log

    def __del__(self):
        self.disconnect_from_server()

    def is_connected(self):
        return self._manager is not None

    def get_dispatcher(self):
        return ClientDispatcher(self)

    def connect_to_server(self, ip="127.0.0.1", port=8013, authkey='12345'):
        try:
            self._manager = ServerQueueManager(address=(ip, port), authkey=bytes(authkey,encoding='utf8'))
            self._manager.connect()
            self._job_queue = self._manager.get_job_queue()
            self._result_queue = self._manager.get_result_queue()
            print('Client connected to %s:%s' % (ip, port))
            return True
        except Exception as e:
            self._manager = None
            self._job_queue = None
            self._result_queue = None
            print('Exception raised by client : ' + str(e))
            return False

    def run(self, command_name, **kwargs):
        if self.is_connected():
            self._job_queue.put((command_name, self._name, kwargs))
            result = self._result_queue.get(block=True)
            return result
        return None

    def disconnect_from_server(self):
        if self.is_connected():
            self._job_queue.put(('close_server', self._name))

