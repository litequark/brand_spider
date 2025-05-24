import random
from time import sleep

def sleep_with_random(interval: int,
                      rand_max: int) -> None:
    rand = random.uniform(0.0, 1.0) * rand_max
    sleep(interval + rand)