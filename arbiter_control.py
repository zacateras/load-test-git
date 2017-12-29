from pulsar import spawn, send, arbiter
from actor_control import *
from git_server import *
import random
import asyncio


class CycleConfig:
    def __init__(self, timeout, git_server_cpus, actor_count):
        self.timeout = timeout
        self.git_server_cpus = git_server_cpus
        self.actor_count = actor_count


class CycleResult:
    def __init__(self):
        pass


class ArbiterControl:
    def __init__(self):
        self._git_server = None
        self._actors = []

        self._log = []

    def __call__(self, arb, **kwargs):
        self._print('START')

        self._arb = arb
        self._arb_task = arb._loop.create_task(self._work())

    async def _work(self):
        cycle_i = 0
        cycle_config = self._next_cycle_config()

        while True:
            # CYCLE - START
            self._print('Starting cycle %s...' % cycle_i)
            self._print('Starting git server...')
            self._git_server = git_server_build(cycle_config.git_server_cpus)

            self._print('Spawning actors...')
            self._actors = []

            for ai in range(cycle_config.actor_count):
                actor = await self._arb.spawn()
                self._actors.append(actor)

            self._print('Scattering tasks...')
            await self._scatter(cycle_config)

            # CYCLE - WAIT FOR TIMEOUT
            for i in range(cycle_config.timeout):
                self._print('%s...' % i)
                await asyncio.sleep(1)

            # CYCLE - END
            self._print('Gathering results...')
            cycle_result = await self._gather(cycle_config)

            self._print('Stopping actors...')
            for actor in self._actors:
                actor.stop()

            self._print('Stopping git server...')
            self._git_server.dispose()

            # CYCLE - LOG RESULT
            self._log.append((cycle_config, cycle_result))

            cycle_i += 1
            cycle_config = self._next_cycle_config()

    def _next_cycle_config(self):
        return CycleConfig(500, 0.5, 10)

    async def _scatter(self, cycle_config: CycleConfig):
        for i in range(cycle_config.actor_count):
            request = {'id': i, 'task_type': 'task_type'}
            response = await send(
                self._actors[i],
                'run',
                actor_scatter_process,
                request)

            self._print(str(response))

    async def _gather(self, cycle_config: CycleConfig):
        for i in range(cycle_config.actor_count):
            response = await send(
                self._actors[i],
                'run',
                actor_gather_process)

            self._print(str(response))

    @staticmethod
    def _print(output):
        print('[ARBITER] ' + output)
