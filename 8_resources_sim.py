import itertools
import random as rand
import simpy as sim


CAR_TANK_LEVEL = 5, 25
CAR_TANK_SIZE = 50
REFUELING_SPEED = 2
# Доля оставшегося топлива на заправке
THRESHOLD = 0.25
TANK_TRUCK_TIME = 300
T_INTER = 30, 300
STATION_TANK_SIZE = 200
RANDOM_SEED = 42
SIM_TIME = 1000


def car(env: sim.Environment, name, gas_station, station_tank):
    """Заправка автомобиля.
    """
    # Уровень топлива в баке автомобиля
    car_tank_level = rand.randint(*CAR_TANK_LEVEL)
    print(f'{env.now:6.1f} с: {name} приехало на заправку')
    
    # Запрос доступа к ресурсу (к бензоколонке)
    with gas_station.request() as req:
        # Ожидание доступа
        yield req
        # Доступ получен

        fuel_required = CAR_TANK_SIZE - car_tank_level
        # Автомобиль заправляет полный бак,
        # забрав несколько литров из цистерны заправки
        yield station_tank.get(fuel_required)

        # Заправка занимает некоторое время
        yield env.timeout(fuel_required / REFUELING_SPEED)

        print(f'{env.now:6.1f} с: {name} заправлено {fuel_required:.1f} л')


def car_generator(env: sim.Environment, gas_station, station_tank):
    """Машины приезжают в случайные моменты времени.
    """
    for i in itertools.count():
        yield env.timeout(rand.randint(*T_INTER))
        # Приехала машина -> запускаем её процесс
        env.process(car(env, f'Авто {i}', gas_station, station_tank))


def gas_station_control(env: sim.Environment, station_tank):
    """Периодический процесс контроля уровня топлива
    в заправочной цистерне.
    """
    while True:
        if station_tank.level / station_tank.capacity < THRESHOLD:
            # Осталось мало топлива -> вызов бензовоза
            print(f'{env.now:6.1f} с: Вызов бензовоза')
            # Ожидание завершения процесса бензовоза
            yield env.process(tank_truck(env, station_tank))

        # Контроль осуществляется каждые 10 сек.
        yield env.timeout(10)


def tank_truck(env: sim.Environment, station_tank):
    """Процесс пополнения заправочной цистерны бензовозом.
    """
    # Ожидание прибытия
    yield env.timeout(TANK_TRUCK_TIME)
    # Заправка заправки
    amount = station_tank.capacity - station_tank.level
    station_tank.put(amount)
    print(
        f'{env.now:6.1f} s: '
        f'Бензовоз прибыл и пополнил запасы заправки ({amount:.1f} л)'
    )


# Исходные данные
print('Заправка полностью заполнена')
rand.seed(RANDOM_SEED)

# Инициализация среды
env = sim.Environment()
# - на заправке 2 колонки
gas_station = sim.Resource(env, 2)
station_tank = sim.Container(env, STATION_TANK_SIZE, init=STATION_TANK_SIZE)
# - начальные процессы:
#   генерация машин и контроль уровня топлива на заправке
env.process(gas_station_control(env, station_tank))
env.process(car_generator(env, gas_station, station_tank))

# Моделирование
env.run(until=SIM_TIME)
