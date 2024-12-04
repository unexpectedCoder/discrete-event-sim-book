from dataclasses import dataclass, field
from typing import Callable, List, Union
from queue import PriorityQueue


@dataclass(order=True, frozen=True)
class Event:
    when: Union[int, float]
    actions: List[Callable] = field(compare=False)


def lights():
    global events

    if current_lights is RED:
        events.put(Event(
            when=now + t_red,
            actions=[red2green, lights]
        ))
    else:
        events.put(Event(
            when=now + t_green,
            actions=[green2red, lights]
        ))


def red2green():
    global current_lights
    current_lights = GREEN
    print(f"{now}\t{current_lights}")


def green2red():
    global current_lights
    current_lights = RED
    print(f"{now}\t{current_lights}")


def des_loop(processes, until):
    global now, events

    for proc in processes:
        proc()
    
    while not events.empty():
        event = events.get()
        if event.when > until:
            break

        now = event.when

        for action in event.actions:
            action()


# Возможные состояния светофора
RED, GREEN = "RED", "GREEN"
# Текущее состояние светофора
current_lights = RED
# Время работы светофора в двух режимах
t_red, t_green = 1, 2
# Текущее модельное время
now = 0
# Очередь событий
events = PriorityQueue()

print("Time\tCurrent lights")
print(f"{now}\t{current_lights}")

processes = [lights]
des_loop(processes, until=7)
