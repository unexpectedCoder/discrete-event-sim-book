import random as rand
import simpy as sim
from collections import namedtuple


# Простая структура данных клиента
Client = namedtuple("Client", "cid arrival duration")


def clients_arriving(env: sim.Environment,
                     clients: sim.Store,
                     mean_arrival: float):
    """Процесс прихода клиентов.

    * env: экземпляр среды SimPy
    * clients: разделяемый ресурс - очередь клиентов
    * mean_arrival: среднее время между приходами клиентов
    """
    # cid - индивидуальный номер клиента
    cid = 1

    while True:
        # Ожидаем нового клиента через случайное время
        yield env.timeout(rand.expovariate(1/mean_arrival))
        # При наступлении события выполняем callback-код:
        # создаём нового клиента
        new_client = Client(cid, env.now, rand.uniform(1/60, 1/6))
        print(f"{env.now:.4f}: Клиент #{new_client.cid} ПРИШЁЛ")

        # Ожидаем возможности добавить клиента в очередь:
        # в данном случае выполняется сразу,
        # поскольку размер очереди не ограничен
        yield clients.put(new_client)
        # После выполняется callback-код
        cid += 1


def window(env: sim.Environment,
           timed_agenda: list[tuple[float, float]],
           clients: sim.Store,
           win_num: int):
    """Процесс работы окошка.

    * env: экземпляр среды SimPy
    * timed_agenda: расписание работы окна
    * clients: очередь клиентов (разделяемый ресурс)
    * win_num: номер окошка
    """
    # ts, te - время открытия и закрытия окошка
    for ts, te in timed_agenda:
        # Ожидание открытия окна
        yield env.timeout(ts - env.now)
        print(
            f"{env.now:.4f}: Окно #{win_num} ОТКРЫЛОСЬ"
        )

        # Ожидание окончания процесса обслуживания
        # клиентов (очереди clients).
        # Процесс завершится, когда окошко закроется на перерыв
        yield env.process(service(env, clients, te, win_num))
        # Внутри service бесконечный цикл, который прерывается,
        # когда окошко закрывается на перерыв.
        # Это приводит к новой итерации цикла for =>
        # позже окошко откроется по расписанию в момент времени ts


def service(env: sim.Environment,
            clients: sim.Store,
            when_close: float,
            win_num: int):
    """Процесс обслуживания клиентов до тех пор,
    пока окошко не закроется на перерыв в момент времени
    `when_close` или после обслуживания последнего клиента,
    вышедшего за рамки данного времени.

    * env: экземпляр среды SimPy
    * clients: очередь клиентов (разделяемый ресурс)
    * when_close: когда окошку закрываться на перерыв
    * win_num: номер обслуживающего окошка
    """
    while True:
        # Запрос на получение ресурса
        with clients.get() as client_req:
            dt = when_close - env.now
            if dt < 0:
                # Условие закрытия окна
                print(f"{env.now:.4f}: Окно #{win_num} ЗАКРЫЛОСЬ")
                return
            close = env.timeout(dt)
            # Ожидаем либо получения ресурса,
            # либо наступления перерыва
            event = yield client_req | close
            # В event хранится словарь {событие: значение_события}

            # Если получили доступ к ресурсу:
            if client_req in event:
                # - достаём соответствующий экземпляр клиента
                client: Client = client_req.value
                print(
                    f"{env.now:.4f}: Окно #{win_num} ЗАНЯТО "
                    f"Клиентом #{client.cid}"
                )

                # - ожидаем, пока клиент обслуживается
                yield env.timeout(client.duration)
                print(f"{env.now:.4f}: Окно #{win_num} СВОБОДНО")
            else:
                # - ещё одно условие закрытия окна
                print(f"{env.now:.4f}: Окно #{win_num} ЗАКРЫЛОСЬ")
                return


# Затравка для воспроизведения случайных чисел
rand.seed(42)
# Инициализируем среду SimPy с указанием начального времени
env = sim.Environment(initial_time=8.5)
# Назначаем расписание работы трёх окон
windows_work_time = [
    [(8.5, 10.5), (11.5, 13.5)],
    [(8.5, 9.5), (10.5, 12.5)],
    [(11.5, 14.5)]
]

# Инициализируем разделяемый ресурс - очередь клиентов
clients = sim.Store(env)
# Запускаем процесс прихода клиентов
env.process(
    clients_arriving(env, clients, mean_arrival=1/3)
)
# Запускаем три процесса работы окон.
# Каждое окно со своим расписанием работы timed_agenda
for i, timed_agenda in enumerate(windows_work_time):
    # Обратите внимание, что одну и ту же функцию, но с разными
    # аргументами, мы используем, чтобы создать
    # три различных процесса (для каждого окна)
    env.process(window(env, timed_agenda, clients, i+1))

# Запускаем симуляцию
env.run(until=11)
