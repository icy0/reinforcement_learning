import simpy
import random
import numpy
import math
import matplotlib.pyplot as plt
import io
import os
import sys
import pygame
from pygame.locals import *

# simulation-wide constants
############################
NUMBER_OF_ELEVATORS = 3
NUMBER_OF_PEOPLE_AT_START = 0
MAX_PEOPLE_PER_ELEVATOR = 5
TIME_PER_STORY = 3 # how much time the elevator needs to travel between two adjacent stories in seconds
NUMBER_OF_STORIES = 15
SIMULATION_TIME = 60 * 60 * 24 # seconds per day
HUMAN_IDLE_TIME_MIN = 100
HUMAN_IDLE_TIME_MAX = 500
HUMAN_SPAWN_CHANCE_INTERVAL = 10 # seconds in between spawn tries
HUMAN_DESPAWN_CHANCE_INTERVAL = 10 # seconds in between despawn tries
############################
# pygame constants
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 1050
CHART_SCALE_FACTOR = 2/3
############################

class Elevator(object):
    next_id = 0
    ascending_queues = list()
    descending_queues = list()
    for i in range(0, NUMBER_OF_STORIES):
        ascending_queues.append(list())
        descending_queues.append(list())

    def __init__(self, env):
        self.id = Elevator.next_id
        Elevator.next_id += 1
        self.env = env
        self.story = 1
        self.load = list()
        self.ascending = True # True -> elev goes up, False -> elev goes down

    def work(self):
        while(True):
            while(self.ascending and self.story <= NUMBER_OF_STORIES):
                self.drop_on_story(self.story)
                self.pick_up_on_story(self.story)
                log("Elevator " + str(self.id) + " ascending.")
                yield self.env.timeout(TIME_PER_STORY)
                self.story += 1
                log("Elevator " + str(self.id) + " arrived on story " + str(self.story) + ".")
                if(self.story == NUMBER_OF_STORIES):
                    self.ascending = False
            while((not self.ascending) and self.story >= 1):
                self.drop_on_story(self.story)
                self.pick_up_on_story(self.story)
                log("Elevator " + str(self.id) + " descending.")
                yield self.env.timeout(TIME_PER_STORY)
                self.story -= 1
                log("Elevator " + str(self.id) + " arrived on story " + str(self.story) + ".")
                if(self.story == 1):
                    self.ascending = True

    @staticmethod
    def request(human, ascending):
        log("Human No. " + str(human.id) + " requested elevator on story " + str(human.location) + " with destination " + str(human.destination) + ".")
        if(ascending):
            Elevator.ascending_queues[human.location - 1].append(human)
        else:
            Elevator.descending_queues[human.location - 1].append(human)
            
    def pick_up_on_story(self, story):
        while(self.ascending and len(self.ascending_queues[story - 1]) > 0 and len(self.load) < MAX_PEOPLE_PER_ELEVATOR):
            human = self.ascending_queues[story - 1].pop(0)
            self.load.append(human)
            human.pickup_event.succeed()
            human.pickup_event = self.env.event()
            log("Picking up human No. " + str(human.id) + " on story " + str(story) + ". Current load: " + str(len(self.load)) + ".")
        while(not self.ascending and len(self.descending_queues[story - 1]) > 0 and len(self.load) < MAX_PEOPLE_PER_ELEVATOR):
            human = self.descending_queues[story - 1].pop(0)
            self.load.append(human)
            human.pickup_event.succeed()
            human.pickup_event = self.env.event()
            log("Picking up human No. " + str(human.id) + " on story " + str(story) + ". Current load: " + str(len(self.load)) + ".")

    def drop_on_story(self, story):
        for human in self.load:
            if(human.destination == story):
                self.load.remove(human)
                log("Dropping human No. " + str(human.id) + " on story " + str(story) + ". Current load: " + str(len(self.load)) + ".")
                human.location = story
                human.dropoff_event.succeed()
                human.dropoff_event = self.env.event()

class Human(object):
    next_id = 0

    def __init__(self, env, elevators):
        self.id = Human.next_id
        Human.next_id += 1
        self.env = env
        self.came_to_live_at = env.now
        self.location = 1
        self.destination = random.randint(1, NUMBER_OF_STORIES)
        while(self.destination == self.location):
            self.destination = random.randint(1, NUMBER_OF_STORIES)
        self.elevators = elevators
        self.pickup_event = env.event()
        self.dropoff_event = env.event()
        self.alive = True
        self.own_waiting_times = list()

    def live(self):
        while(self.alive):
            while(self.destination == self.location):
                self.destination = random.randint(1, NUMBER_OF_STORIES)
            is_ascending = self.location < self.destination
            Elevator.request(human=self, ascending=is_ascending)
            waiting_start_time = env.now
            yield self.pickup_event
            waiting_end_time = env.now
            self.own_waiting_times.append(waiting_end_time - waiting_start_time)
            waiting_times.append(waiting_end_time - waiting_start_time)
            yield self.dropoff_event
            log("Human No. " + str(self.id) + " arrived at story " + str(self.location) + ", now idling for some seconds.")
            yield self.env.timeout(random.randint(HUMAN_IDLE_TIME_MIN, HUMAN_IDLE_TIME_MAX))

    def die(self):
        self.alive = False

def chance_of_spawning_normalized(x):
    return 0.4 - (2.0 * x - 1.0) * (2.0 * x - 1.0)

def chance_of_despawning_normalized(x):
    return 0.6 - ((x-1) * (x-1))

def spawn_humans():
    while(True):
        chance = chance_of_spawning_normalized(env.now / SIMULATION_TIME)
        if(random.random() < chance):
            human = Human(env, elevators)
            humans.append(human)
            env.process(human.live())
            log("Spawned human No. " + str(human.id) + ".")
        yield env.timeout(HUMAN_SPAWN_CHANCE_INTERVAL)

def despawn_humans():
    while(True):
        chance = chance_of_despawning_normalized(env.now / SIMULATION_TIME)
        if(random.random() < chance and len(humans) > 0):
            human = humans.pop(0)
            if(len(human.own_waiting_times) > 0):
                average_waiting_times_per_human.append(numpy.mean(human.own_waiting_times))
            human.die()
            log("Despawned human No. " + str(human.id) + ".")
        yield env.timeout(HUMAN_DESPAWN_CHANCE_INTERVAL)

def log(x):
    time_in_s = env.now
    hours = int(env.now / (60*60))
    minutes = int((env.now - (hours*60*60)) / 60)
    seconds = int(env.now - (hours*60*60 + minutes*60))
    time_in_hms = str(hours) + ":" + str(minutes) + ":" + str(seconds)
    logfile.write(time_in_hms + " -> " + x + "\n")

def log_human_count():
    while(True):
        human_count_every_second.append(len(humans))
        yield env.timeout(1)

seed = 102302338232934
seed_path = "C:\Development\simulation_and_reinforcement_learning\\" + str(seed) + "\\"
if not os.path.exists(seed_path):
    os.makedirs(seed_path)

random.seed(seed)
env = simpy.Environment()
logfile = open(seed_path + "log_" + str(seed) + ".txt", mode='wt')
statsfile = open(seed_path + "stats_" + str(seed) + ".txt", mode='wt')
humans = list()
elevators = list()
waiting_times = list()
human_count_every_second = list()
average_waiting_times_per_human = list()
# env = simpy.rt.RealtimeEnvironment(strict=False, factor=0.1)
for i in range(0, NUMBER_OF_ELEVATORS):
    elevator = Elevator(env)
    elevators.append(elevator)
    env.process(elevator.work())
for i in range(0, NUMBER_OF_PEOPLE_AT_START):
    human = Human(env, elevators)
    env.process(human.live())
    logfile.write(str(env.now) + ": Spawned human No. " + str(human.id) + ".\n")

env.process(spawn_humans())
env.process(despawn_humans())
env.process(log_human_count())
env.run(SIMULATION_TIME)

plt.rcdefaults()
plt.rcParams.update({'axes.facecolor':'#EFEFEF', 'figure.facecolor':'#EFEFEF'})
plt.xlabel("Tageszeit in [s]")
plt.ylabel("Menschenanzahl")
plt.plot(human_count_every_second)
plt.savefig(seed_path + "humans_alive_seed_" + str(seed) + ".png")
plt.clf()
plt.xlabel("einzelne Wartephasen")
plt.ylabel("Wartezeit in [s]")
plt.plot(waiting_times)
plt.savefig(seed_path + "waiting_times_seed_" + str(seed) + ".png")
plt.clf()
plt.xlabel("Durchschnittliche Wartezeit pro Mensch")
plt.ylabel("Wartezeit in [s]")
plt.plot(average_waiting_times_per_human)
plt.savefig(seed_path + "average_waiting_times_per_human_seed_" + str(seed) + ".png")
plt.clf()
plt.boxplot(x=average_waiting_times_per_human)
plt.savefig(seed_path + "average_waiting_times_per_human_seed_boxplot_" + str(seed) + ".png")

stats_stringlines = list()
stats_stringlines.append("STATISTICS:")
stats_stringlines.append("___________")
stats_stringlines.append("")
stats_stringlines.append("humans simulated: " + str(Human.next_id))
stats_stringlines.append("maximum humans alive: " + str(numpy.max(human_count_every_second)))
stats_stringlines.append("")
stats_stringlines.append("")
stats_stringlines.append("WAITING TIME:")
stats_stringlines.append("_____________")
stats_stringlines.append("mean   [s]: " + str(numpy.mean(waiting_times)))
stats_stringlines.append("median [s]: " + str(numpy.median(waiting_times)))
stats_stringlines.append("max    [s]: " + str(numpy.max(waiting_times)))
stats_stringlines.append("min    [s]: " + str(numpy.min(waiting_times)))
stats_stringlines.append("")
stats_stringlines.append("mean of human means   [s]: " + str(numpy.mean(average_waiting_times_per_human)))
stats_stringlines.append("median of human means [s]: " + str(numpy.median(average_waiting_times_per_human)))
stats_stringlines.append("max of human means    [s]: " + str(numpy.max(average_waiting_times_per_human)))
stats_stringlines.append("min of human means    [s]: " + str(numpy.min(average_waiting_times_per_human)))

for line in stats_stringlines:
    statsfile.write(line)
statsfile.close()

pygame.init()
surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

pygame.font.init()

font = pygame.font.SysFont("LiberationMono", 20)
text_surfaces = list()
for statline in stats_stringlines:
    text_surfaces.append(font.render(statline, True, (0x3A, 0x3A, 0x3A), None))
pygame.draw.rect(surface, (0xEF, 0xEF, 0xEF), (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

humans_alive_chart = pygame.image.load(seed_path + "humans_alive_seed_" + str(seed) + ".png")
humans_alive_chart = pygame.transform.smoothscale(humans_alive_chart, (humans_alive_chart.get_rect().width * CHART_SCALE_FACTOR, humans_alive_chart.get_rect().height * CHART_SCALE_FACTOR))

waiting_times_chart = pygame.image.load(seed_path + "waiting_times_seed_" + str(seed) + ".png")
waiting_times_chart = pygame.transform.smoothscale(waiting_times_chart, (waiting_times_chart.get_rect().width * CHART_SCALE_FACTOR, waiting_times_chart.get_rect().height * CHART_SCALE_FACTOR))

average_waiting_times_chart = pygame.image.load(seed_path + "average_waiting_times_per_human_seed_" + str(seed) + ".png")
average_waiting_times_chart = pygame.transform.smoothscale(average_waiting_times_chart, (average_waiting_times_chart.get_rect().width * CHART_SCALE_FACTOR, average_waiting_times_chart.get_rect().height * CHART_SCALE_FACTOR))

while(True):
    y_accum = 0
    for statline in text_surfaces:
        surface.blit(statline, (humans_alive_chart.get_rect().width, y_accum))
        y_accum += 22
    surface.blit(humans_alive_chart, dest=(0, 0))
    surface.blit(waiting_times_chart, dest=(0, humans_alive_chart.get_rect().height))
    surface.blit(average_waiting_times_chart, dest=(0, humans_alive_chart.get_rect().height + waiting_times_chart.get_rect().height))
    pygame.display.update()
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
