import simpy as sim


# Ожидание завершения процесса
def parts_manufacturing(env: sim.Environment):
    for i, manufacturing_time in enumerate([2, 1, 4]):
        yield env.timeout(manufacturing_time)
        print(f"{env.now}: деталь {i+1} изготовлена")


def parts_covering(env: sim.Environment, proc_before):
    yield proc_before
    print(
        f"{env.now}: транспортировка в цех нанесения покрытий"
    )
    yield env.timeout(1)
    print(f"{env.now}: начинается покрытие деталей")
    yield env.timeout(10)
    print(f"{env.now}: покрытие нанесено")


env = sim.Environment()
proc = env.process(parts_manufacturing(env))
env.process(parts_covering(env, proc))
env.run()

print()
# ----------------------------


# Условные события
def condition_process(env: sim.Environment, another_proc):
    event = yield another_proc | env.timeout(3)
    what_event = type(list(event.keys())[0])
    print(f"{env.now}: случилось событие {what_event}")


def process(env: sim.Environment):
    yield env.timeout(5)
    print(f"{env.now}: process завершён")


env = sim.Environment()
cond_proc = env.process(process(env))
env.process(condition_process(env, cond_proc))
env.run()

print()
# ----------------


# Взаимодействие процессов
def students(env: sim.Environment):
    while True:
        yield ring_bell
        print(f"{env.now}: перемена!")


def school(env: sim.Environment):
    global ring_bell

    for _ in range(5):
        print(f"{env.now}: начался урок :(")
        yield env.timeout(45)

        ring_bell.succeed()
        ring_bell = env.event()

        yield env.timeout(10)


env = sim.Environment()
ring_bell = env.event()
env.process(school(env))
env.process(students(env))
env.run()
print()
# ------------------------


# Прерывание процесса другим
# --------------------------
def some_process(env: sim.Environment):
    while True:
        try:
            yield env.timeout(2)
            print(f"{env.now}: some_process в работе")
        except sim.Interrupt:
            print(f"{env.now}: some_process прерван")
            return


def another_process(env: sim.Environment, proc: sim.Process):
    yield env.timeout(5)
    print(f"{env.now}: another_process прерывает some_process")
    proc.interrupt()


env = sim.Environment()
proc = env.process(some_process(env))
env.process(another_process(env, proc))
env.run()
# --------------------------
