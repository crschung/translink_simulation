import random
import numpy as np
import math
import heapq
import matplotlib.pyplot as plt
from scipy.stats import truncnorm
random.seed(1)

class Bus:
    """Bus Class
    
        The Bus class stores information on the bus, the current amount of passengers
        on the bus and it's corresponding stops and position. It also keeps track on the timing
        on when to let people in and off the bus
        
        Parameters:
        
        run_time: the run time of the current bus
        stops: the stops the bus will stop at
        capcity: the maximum capacity of pasengers the bus can hold (Translink 40-foot buses hold a maximum of 52 people)
        passengers: the passengers who are currently on the bus
        
        For Statstics:
        
        max_passengers: the maximum amount of passengers the bus has held at a time
        run_time: the run time of the bus from start to end
    """
    def __init__(self,position):
        self.position = position
        self.capacity = 100
        self.passengers = []
        self.max_pass = 0
        self.last = False
        self.active = False
    
    def remaining_cap(self):
        return self.capacity - len(self.passengers)
    
    
    def enter_Bus(self, passengers):
        if np.iterable(passengers):
            self.passengers.extend(passengers)
            self.max_pass += len(passengers)
        else:
            self.passengers.append(passengers)
            self.max_pass += 1
            
    def exitBus(self, stop_number, exit_time):
        exit_passengers = [passenger for passenger in self.passengers if passenger.arrival_stop == stop_number]
        t = 0.0
        for p in exit_passengers:
            self.passengers.remove(p)
            t += exit_time
        return t, exit_passengers
    
    def empty(self, cur_time):
        for passenger in self.passengers:
            passenger.end_time = cur_time
            passenger.dest = self.position
        out_passengers = self.passengers
        self.passengers = []
        self.active = False
        return out_passengers

class Passenger():
    """Passenger Class
    
        The Passenger class stores information the passenger on where they want to 
        get on and off the bus as well as their time entering and exiting the bus system
        
        Parameters:
        
        depart_stop: Stop the passenger is departing from
        arrival_stop: Stop the passenger is arriving to
        
        Both of the above parameters contain the bus stop position index on the circuit
        
        start_time: When the passenger arrives to the stop
        end_time: When the passenger leaves the bus
        
    """
    def __init__(self,time,depart,dest):
        self.depart_stop = depart
        self.arrival_stop = dest
        self.start_time = time
        self.end_time = None
        

class BusStop():
    """BusStop Class
    
        A bus stop is locates somewhere along the bus' route. Passengers are pre-determined
        and generated upon Initialization of the bus stop in a Poisson distribution.
        When the bus reaches the bus stop, passengers enter the bus in a FIFO priority with the remaining passengers
        left behind for the next bus.
        
        Parameters:
        
        passengers: Passengers who are waiting at the bus stop
        position: Bus stop's position on the route
        average_passengers: Mean of passeners who usually wait at the stop
        next_arrival_time: Arrival time between passengers arriving at the bus stop
        
    """
    def __init__(self, position, arrival_time):
        self.arrival_time = arrival_time
        self.passengers = []
        self.position = position
        self.next_arrival_time = -5* math.log(random.random())
        
    def generatePassenger(self, time, arrival_stop):
            self.passengers.append(Passenger(0,time,arrival_stop))
        
    def enterBus(self,bus,hop_on_off):
        run_time = 0.0
        nb_to_bus = min(bus.remaining_cap(), len(self.passengers))
        for i in range(nb_to_bus):
            passenger = self.passengers.pop()
            bus.enter_Bus(passenger)
            run_time += hop_on_off
        return run_time
            
            
class Event:
    
    def __init__(self, e_time, e_obj):
        self.e_time = e_time
        self.e_obj = e_obj
        
    def __lt__(self, other):
        return self.e_time < other.e_time
        
class Simulation():
    """
    General Structure:
    
    Intialize Bus 
    Generate Passengers for all stops
    Bus Simulation Starts
    People getting off bus?
    If Yes: Record exit times and update passenger queue on bua
    Stop has Passengers?
    If Yes: Record entry times and update passenger queue on bus
    Exit Stop
    Is it the last stop?
    Yes: End bus and run stas
    No: Go back to people getting off bus
    
    """
    def __init__(
            self,
            passenger_arrival_time= -1.5 *math.log(random.random()),
            hop_in_time=-0.5 *math.log(random.random()),
            hop_out_time=-0.5 *math.log(random.random()),
            nb_stops_to_dest=-5*math.log(random.random()),
            bus_speed= -5*math.log(random.random()),
            nb_buses=50,
            time_between_buses= -7*math.log(random.random()),
            delay_time = 0.5):
        
        self.hop_in_time = hop_in_time
        self.hop_out_time = hop_out_time
        self.nb_stops_to_dest = nb_stops_to_dest
        self.bus_speed = bus_speed
        self.nb_buses = nb_buses
        self.time_between_buses = time_between_buses
        self.delay_time = delay_time
        self.stats = None
        self.stops = [BusStop(i,passenger_arrival_time) for i in range(0,numberOfStops)]
        self.stops[-1].arrival_time = np.Inf
            
    def run(self):
        moved_passengers = []
        events = []
        
        # Initialize events queue.
        for stop in self.stops:
            heapq.heappush(events, Event(stop.next_arrival_time, stop))
            
            
        buses = []
        # first bus starts early to avoid over accumulation of passengers at
        # bus stops.
        t = 0.5 * self.time_between_buses
        for i in range(self.nb_buses):
            bus = Bus(0)
            buses.append(bus)
            heapq.heappush(events, Event(t, bus))
            t += self.time_between_buses
        buses[-1].last = True

        # Initialize statistics collection.
        average_runtime = 0
        average_passengers = 0
        overcrowded_passengers = 0
        
        while events:
            event = heapq.heappop(events)
            t, obj = event.e_time, event.e_obj
            average_runtime = t
            if isinstance(obj, BusStop):
                # New arrival at a bus stop.
                dest = obj.position + self.nb_stops_to_dest
                obj.generatePassenger(t, dest)
                heapq.heappush(events, Event(t + obj.next_arrival_time + self.delay_time, obj))
            elif isinstance(obj, Bus):
                if not obj.active:
                    obj.active = True
                if obj.position+1 >= len(self.stops):
                    # Bus reached terminal: it empties and becomes inactive.
                    moved_passengers.extend(obj.empty(t))
                    if obj.last:
                        break
                elif self.stops[obj.position].position == obj.position:
                    # Bus reached a bus stop.
                    bus_stop = self.stops[obj.position]
                    # Passengers hop out.
                    wait_out, passengers = obj.exitBus(
                        stop_number=bus_stop.position,
                        exit_time=self.hop_out_time)
                    moved_passengers.extend(passengers)
                    # Passengers hop in.
                    wait_in = bus_stop.enterBus(obj, self.hop_in_time)
                    obj.position += 1
                    heapq.heappush(events, Event(t + wait_out + wait_in, obj))
                else:
                    # Bus finished loading passengers, move to next stop.
                    dist = self.stops[obj.position+1].position - obj.position
                    heapq.heappush(events,
                                   Event(t + self.bus_speed * dist + self.delay_time, obj))
                    obj.position += dist
                    
        print("%.2f" % average_runtime)
        
if __name__ == "__main__":
    seeds = np.arange(10,60,10)
    for seed in seeds:
        random.seed(seed)
        numberOfStops = 77
        frequency = 7
        time_between_buses = random.expovariate(1./frequency)
        delay_time = 0.1
        numberOfBuses = round(60 / frequency)
        time_bw_stops = 0.2
        sim = Simulation(numberOfStops,time_between_buses=time_between_buses, nb_buses=numberOfBuses, bus_speed=time_bw_stops, delay_time=delay_time)
        sim.run()
    