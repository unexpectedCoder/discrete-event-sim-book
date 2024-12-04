import logging
import random as rand
import simpy as sim


class Client:
    """Описывает клиента.

    # Поля

    * av_wait_time: среднее время ожидания (терпение)
    * av_service_time: среднее время обслуживания
    * env: экземпляр среды SimPy
    * cid: индивидуальный номер
    * arrive_time: время прихода
    * satisfied: удовлетворён ли клиент
    * waiting_time: итоговое время ожидания
    * total_time: общее время, проведённое в банке
    """
    
    av_wait_time = 15/60
    av_service_time = 10/60

    def __init__(self, env: sim.Environment, cid: int):
        self.env = env
        self.cid = cid

        self.arrive_time = env.now
        self.satisfied = False
        self.waiting_time = 0
        self.total_time = 0
    
    def get_service(self, workers: sim.Store):
        """Процесс ожидания обслуживания кем-либо из работников `workers`.

        * workers: разделяемый ресурс - работающие сотрудники банка
        """
        # Запрашиваем ресурс
        with workers.get() as worker_req:
            dt_patience = rand.expovariate(1 / self.av_wait_time)
            patience = self.env.timeout(dt_patience)
            # Ожидаем либо освобождения сотрудника, либо конца терпения
            worker_or_patience = yield worker_req | patience

            # Запоминаем итоговое время ожидания
            self.waiting_time = self.env.now - self.arrive_time

            # Если нашёлся свободный сотрудник:
            if worker_req in worker_or_patience:
                # - достаём экземпляр работника
                worker = worker_req.value
                logging.info(
                    f"{self.env.now:.4f}: "
                    f"Worker #{worker.wid} STARTS service "
                    f"the Client #{self.cid}"
                )

                # - клиент ожидает завершения процесса своего обслуживания
                yield self.env.process(worker.service(self))
                logging.info(
                    f"{self.env.now:.4f}: "
                    f"Worker #{worker.wid} ENDS service "
                    f"the Client #{self.cid}"
                )
                # - клиент удовлетворён
                self.satisfied = True
                # - запоминаем общее время, которое клиент провёл в банке
                self.total_time = self.env.now - self.arrive_time
            # Иначе:
            else:
                # - необслуженный клиент уходит из банка
                logging.info(
                    f"{self.env.now:.4f}: Client #{self.cid} is GONE"
                )


class Worker:
    """Описывает банковского работника.

    # Поля

    * env: SimPy-среда
    * wid: индивидуальный номер работника
    * timed_agenda: расписание работы
    * when_end: когда ближайший перерыв
    * clients: список обслуженных клиентов
    * start_event: событие "сотрудник приступил к работе"
    * get_free_event: событие "сотрудник освободился"
    """

    def __init__(self,
                 env: sim.Environment,
                 wid: int,
                 timed_agenda: list[tuple[float, float]]):
        self.env = env
        self.wid = wid
        self.timed_agenda = timed_agenda

        self.when_end: float = None
        self.clients = []
        
        # Инициализируем элементарные события sim.Event().
        # Их смысл раскрывается в процессах work, service и
        # в процессах банка _add_workers и _free_workers
        self.start_event = env.event()
        self.get_free_event = env.event()
    
    def work(self):
        """Процесс работы сотрудника.
        """
        # Код аналогичен коду работы почтовых окон
        # из предыдущего раздела
        for ts, te in self.timed_agenda:
            self.when_end = te
            
            # Ожидаем начала работы
            yield self.env.timeout(ts - self.env.now)
            logging.info(
                f"{self.env.now:.4f}: Worker #{self.wid} WORKS"
            )

            # Особенность: активируем событие "сотрудник начал работу",
            # причём в качестве параметра succeed передаём
            # текущий экземпляр self, что позволяет процессам
            # обмениваться данными - переданный экземпляр является
            # возвращаемым значением при наступлении события
            self.start_event.succeed(self)
            # И сразу создаём новое событие,
            # ведь работник может уйти на перерыв, после которого
            # снова возобновит работу
            self.start_event = self.env.event()

    def service(self, client: Client):
        """Процесс обслуживания клиента `client`.
        """
        dt = rand.expovariate(1/client.av_service_time)

        # Обслуживаем клиента
        yield self.env.timeout(dt)
        # Добавляем в собственный список обслуженных клиентов
        self.clients.append(client)

        if env.now < self.when_end:
            # Работник продолжает работать,
            # активируя событие "сотрудник освободился"
            self.get_free_event.succeed(self)
            self.get_free_event = self.env.event()
        else:
            # Работник уходит на перерыв
            logging.info(
                f"{self.env.now:.4f}: Worker #{self.wid} RELAXES"
            )


class Bank:
    """Описывает банк, в котором работают сотрудники
    и в который приходят клиенты.

    # Поля

    * av_incoming_time: среднее  время между приходом клиентов
    * env: SimPy-среда
    * workers_list: простой список сотрудников
    * workers: разделяемый ресурс - работающие сотрудники
    * clients: список всех клиентов (обслуженных и нет) банка
    """

    av_incoming_time = 6/60

    def __init__(self, env: sim.Environment, workers: list[Worker]):
        self.env = env
        
        self.workers_list = workers.copy()
        # Ёмкость ресурса ограничена числом работников.
        # Ресурс изначально пуст.
        # Работники будут добавляться при начале работы
        # по своему расписанию
        self.workers = sim.Store(env, len(workers))
        self.clients: list[Client] = []

    def operate(self):
        """Основной процесс функционирования банка.

        Банк запускает процессы работы своих сотрудников,
        а также процессы управления сотрудниками
        и процесс генерации новых клиентов.
        """
        # Запускаем процессы работы всех сотрудников
        for w in self.workers_list:
            self.env.process(w.work())
        # Запускаем процессы управления работниками
        self.env.process(self._add_workers())
        self.env.process(self._free_workers())
        # Запускаем процесс генерации новых клиентов
        self.env.process(self._clients_incoming())
    
    def _add_workers(self):
        # Процесс, добавляющий работников в ресурс workers
        while True:
            # Формируем список событий по всем работникам
            starts = [w.start_event for w in self.workers_list]
            # Ожидаем наступления хотя бы одного события
            any_of = yield self.env.any_of(starts)
            # any_of есть обычный Python-словарь {событие: значение}
            for worker in any_of.values():
                # Добавляем сотрудников, начавших работать,
                # в очередь (ресурс) свободных сотрудников workers
                yield self.workers.put(worker)
    
    def _free_workers(self):
        # Процесс, добавляющий работников,
        # обслуживших очередного клиента,
        # в ресурс свободных сотрудников workers
        while True:
            # Код аналогичен _add_workers,
            # только событие другое (get_free_event)
            ends = [w.get_free_event for w in self.workers_list]
            any_of = yield self.env.any_of(ends)
            for worker in any_of.values():
                yield self.workers.put(worker)
    
    def _clients_incoming(self):
        # Процесс, генерирующий новых клиентов
        num = 1
        while True:
            # Ожидаем события "пришёл новый клиент"
            yield self.env.timeout(
                rand.expovariate(1/self.av_incoming_time)
            )
            client = Client(self.env, cid=num)
            logging.info(
                f"{self.env.now:.4f}: Client #{client.cid} ARRIVES"
            )

            # Запускаем процесс клиента по ожиданию сотрудника
            self.env.process(
                client.get_service(self.workers)
            )

            # Добавляем клиента в список всех клиентов банка
            self.clients.append(client)
            num += 1

    # Далее идёт блок обычных методов класса,
    # предназначенных для получения той или иной
    # информации по результатам моделирования банка
    def get_number_of_clients(self):
        """Общее число клиентов, посетивших банк.
        """
        return len(self.clients)
    
    def get_number_of_satisfied_clients(self):
        """Каково количество довольных клиентов?
        """
        return len([c for c in self.clients if c.satisfied])
    
    def get_number_of_unsatisfied_clients(self):
        """Каково количество недовольных клиентов?
        """
        return len(self.clients) - self.get_number_of_satisfied_clients()

    def get_average_waiting_time(self):
        """Каково среднее время ожидания по всем клиентам?
        """
        return sum([c.waiting_time for c in self.clients]) / len(self.clients)
    
    def get_average_total_time(self):
        """Каково среднее время нахождения удовлетворённых клиентов в банке?
        """
        satisfied = [c.total_time for c in self.clients if c.satisfied]
        return sum(satisfied) / len(satisfied) if satisfied else 0


# Глобальная область
# - настраиваем логирование
logging.basicConfig(
    level=logging.INFO, filename="bank.log", filemode="w"
)
# - задаём затравку для генератора псевдослучайных чисел
rand.seed(42)
# - инициализируем среду SimPy
initial_time = 9
env = sim.Environment(initial_time)
# - формируем расписание работы сотрудников
#   (длина списка определяет число работников: 2 в данном случае)
timed_agenda = [
    [(initial_time, initial_time+2.5), (initial_time+3.5, initial_time+5)],
    [(initial_time+1, initial_time+3.5), (initial_time+4, initial_time+6)]
]
# - создаём список работников
workers = [
    Worker(env, i+1, ta)
    for i, ta in enumerate(timed_agenda)
]
# - создаём банк
bank = Bank(env, workers)
# - запускаем его основной процесс
#   (но моделирование ещё не запущено)
bank.operate()
# - запускаем симуляцию до заданного времени
t_sim = 2
env.run(until=initial_time + t_sim)

# - обрабатываем результаты
for w in workers:
    print(
        f"Работник #{w.wid} обслужил клиентов ",
        [c.cid for c in w.clients]
    )

n_clients = bank.get_number_of_clients()
n_satisfied = bank.get_number_of_satisfied_clients()
n_unsatisfied = bank.get_number_of_unsatisfied_clients()

print("Всего клиентов:\t", n_clients)
print("Число довольных клиентов:\t", n_satisfied)
print("Число недовольных клиентов:\t", n_unsatisfied)
print(
    "Доля довольных клиентов, %:\t",
    round(n_satisfied/n_clients * 100, 2)
)
print(
    "Среднее время ожидания, мин:\t",
    round(60 * bank.get_average_waiting_time(), 2)
)
print(
    "Среднее время в банке довольных клиентов, мин:\t",
    round(60 * bank.get_average_total_time(), 2)
)
print("Текущее время, ч:\t", round(env.now, 2))
