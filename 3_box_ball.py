import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass, field
from matplotlib.patches import Rectangle
from typing import Callable, List, Tuple, Union
from queue import PriorityQueue


@dataclass(order=True, frozen=True)
class Timeout:
    when: Union[int, float]
    actions: List[Tuple[Callable, Tuple]] = field(compare=False)


def ball_motion(bounds, r, v, traj):
    global now, events

    dt, signs = calc_delay(bounds, r, v)
    events.put(Timeout(
        when=now + dt,
        actions=[
            (update, (dt, signs, traj, r, v)),
            (ball_motion, (bounds, r, v, traj))
        ]
    ))


def calc_delay(bounds, r, v):
    # Распакуем аргументы для удобства
    (x_lb, x_rb), (y_bb, y_tb) = bounds
    x, y = r
    vx, vy = v
    # Вычисляем время (задержку):
    dtx, dty = 0., 0.
    # - в направлении оси Ox
    if vx > 0:
        dtx = (x_rb - x) / vx
    elif vx < 0:
        dtx = (x_lb - x) / vx
    # - в направление оси Oy
    if vy > 0:
        dty = (y_tb - y) / vy
    elif vy < 0:
        dty = (y_bb - y) / vy
    # Определяем, какую проекцию скорости инвертировать
    signs = [1, 1]
    signs[np.argmin((dtx, dty))] = -1
    return min(dtx, dty), signs


def update(dt, signs, traj, r, v):
    global now

    r += v * dt
    v *= signs
    traj.append((now, *r))


def des_loop(processes, until):
    global now, events

    now = 0

    for proc, args in processes:
        proc(*args)
    
    while not events.empty():
        event = events.get()
        if event.when > until:
            break

        now = event.when

        for action, args in event.actions:
            action(*args)


def plot_traj(traj, figax=None, **kw):
    if figax is None:
        fig, ax = plt.subplots()
    else:
        fig, ax = figax
    # Линии траектории
    ax.plot(traj[:, 1], traj[:, 2], **kw)
    # Начальная и конечная точки
    ax.plot(traj[0, 1], traj[0, 2],
            ls="", marker="o", c="purple")
    ax.plot(traj[-1, 1], traj[-1, 2],
            ls="", marker="x", c="purple")
    return fig, ax


events = PriorityQueue()
now = 0

# Условия задачи
box_xy, box_w, box_h = (0, 0), 1, 1
bounds = (box_xy[0], box_w), (box_xy[1], box_h)
r = np.array((0.6, 0.3))
v = np.array((0.3, 0.1))
until = 59

# Решение
# - Сохраним начальную точку траектории
traj = [(now, *r)]
# - Регистируем процесс motion
processes = [
    (ball_motion, (bounds, r, v, traj))
]

# - Запускаем моделирование в течение заданного времени
des_loop(processes, until)

# - Сохраним точку траектории в конце моделирования
r += v * (until - traj[-1][0])
traj.append((until, *r))
traj = np.array(traj)

# Графики
fig, ax = plot_traj(traj)
bounds_rect = Rectangle(
    box_xy, box_w, box_h,
    facecolor="none", edgecolor="k", lw=2
)
ax.add_patch(bounds_rect)
ax.set(xlabel="$x$", ylabel="$y$", aspect="equal")
fig.savefig(f"{__file__.split('.')[0]}.png", dpi=150)

print("Число столкновений:", traj.shape[0] - 1)
