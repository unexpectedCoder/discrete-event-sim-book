from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Union
from queue import PriorityQueue


@dataclass(order=True, frozen=True)
class Timeout:
    when: Union[int, float]
    actions: List[Tuple[Callable, Tuple]] = field(compare=False)


def delayed_echo(text, delay):
    global events

    events.put(Timeout(
        when=now + delay,
        actions=[
            (echo, (text,)),
            (delayed_echo, (text, delay))
        ]
    ))


def echo(text):
    print(f"{now}\t{text}")


def des_loop(processes, until):
    global now, events

    for proc, args in processes:
        proc(*args)

    while not events.empty():
        event = events.get()
        if event.when > until:
            break

        now = event.when
        
        for action, args in event.actions:
            action(*args)


now = 0
events = PriorityQueue()

processes = [
    (delayed_echo, ("A", 3)),
    (delayed_echo, ("B", 2)),
    (delayed_echo, ("C", 5))
]

print("Time\tEcho")
des_loop(processes, until=10)
