import asyncio
import json
from robot import Robot
from vision import Vision


class Server():

    TIMEOUT = 2.0
    
    def __init__(self, *args, **kwargs):
        self.loop = asyncio.get_event_loop()
        self.robot = Robot('MSE430-5', self.loop)
        self.vision = Vision(self.loop)
        self.server = None
        self.commands = {
            'objects': self.objects,
            'robot': self.getrobot,
            'obstacles': self.obstacles,
            'setspeed': self.setspeed,
            'setpower': self.setpower,
            'setparam': self.setparam,
            'help': self.help,
            '?': self.help
        }
        
    def run(self):
        try:
            self.loop.run_until_complete(self.robot.connect())
            asyncio.ensure_future(self.vision.run())
            self.server = self.loop.run_until_complete(
                self.loop.create_server(lambda: ServerProtocol(self),
                                        port=55555))
            print('Serving on {}'.format(
                self.server.sockets[0].getsockname()))
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        print('Exiting')
        self.close()  # Should this be here?

    def stop(self):
        self.loop.stop()

    def close(self):
        self.robot.close()
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

    def objects(self):
        """objects -- Return positions of all tracked objects in view"""

        return json.dumps({'objects': self.vision.objects})

    def getrobot(self):
        """robot -- Return position of the robot"""

        return json.dumps({'robot': self.vision.robot})

    def obstacles(self):
        """obstacles -- Return positions of all obstacles in view"""

        return json.dumps({'obstacles': self.vision.obstacles})

    def setspeed(self, speed_a, speed_b):
        """setspeed speed_a speed_b -- Set motor target speed (?-??)"""
        
        speed_a = int(speed_a)
        speed_b = int(speed_b)
        asyncio.ensure_future(self.robot.set_speed(speed_a, speed_b),
                              loop=self.loop)
        return json.dumps({'speed_a': speed_a, 'speed_b': speed_b})

    def setpower(self, power_a, power_b):
        """setpower power_a power_b -- Directly set motor power (0-500)"""

        power_a = int(power_a)
        power_b = int(power_b)
        asyncio.ensure_future(self.robot.set_power(power_a, power_b),
                              loop=self.loop)
        return 'speed: {:d}, {:d}'.format(speed_a, speed_b)

    def setparam(self, name, value):
        """setparam name value -- Configure the robot (not implemented)"""

        raise NotImplementedError('Nope')

    def help(self, command=None):
        """help | ? [command] -- Display all commands or details of one"""
        if command:
            return self.commands[command.lower()].__doc__
        else:
            return '\n'.join([x.__doc__ for x in self.commands.values()])
        
class ServerProtocol(asyncio.Protocol):
    def __init__(self, server):
        self.server = server
        self.transport = None
        
    def connection_made(self, transport):
        self.transport = transport
        print('Connection made')
        self.write('MSE430 Server (CS 470 BYU)')
        
    def connection_lost(self, exc):
        print('Connection lost')
        self.server.stop()
        
    def write(self, data):
        data = str(data)
        print('Sent: {}'.format(data))
        self.transport.write((data+'\n').encode())

    def data_received(self, data):
        if not data:
            return
        data = data.strip().decode()
        print('Received: {}'.format(data))
        cmd = data.split()[0].lower()
        args = data.split()[1:]
        if cmd in self.server.commands:
            try:
                self.write(self.server.commands[cmd](*args))
            except Exception as e:
                self.write('{} occurred while handling "{}": {}'.format(
                    type(e).__name__, data, str(e)))
                raise e
        else:
            self.write('Unknown command: "{}"'.format(cmd))
            
    def eof_received(self):
        return False


if __name__ == '__main__':
    Server().run()
