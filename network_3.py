import queue
import threading
import ast

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]
        return self(dst, prot_S, data_S)




## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination

    ## called when printing the object
    def __str__(self):
        return self.addr

    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        print()
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
            print()

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return



## Implements a multi-interface router
class Router:

    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        
        self.rt_tbl_D = {}      # {destination: {router: cost}}
        for key in self.cost_D:
            for interface in self.cost_D[key]:
                self.rt_tbl_D[key] = {self.name : self.cost_D[key][interface]}
        self.rt_tbl_D[self.name] = {self.name : 0}
        
        print('%s: Initialized routing table' % self)
        self.print_routes()


    ## Print routing table
    def print_routes(self):
        
        dest_list = list(self.rt_tbl_D)
        
        for dest in range(len(dest_list) + 1):
            print('=======', end = '')
        
        print()
        print('|| ' + self.name + ' ||', end = '')
        
        for dest in dest_list:
            print('  ' + dest + '  ', end = '|')
        
        router_list = list(self.rt_tbl_D[dest_list[0]])
        
        print()
        for dest in range(len(dest_list) + 1):
            print('=======', end = '')
        
        print()
        for router in sorted(router_list):
            print('|  ' + router + '  ', end = '|')
        
            for dest in self.rt_tbl_D:
                print('   ' + str(self.rt_tbl_D[dest][router]) + '  ', end = '|')
            print()
        
            for dest in range(len(dest_list) + 1):
                print('-------', end = '')
            print()
        
        
    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))


    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            outgoing_interface = 1
            found = False
            check_val = float("inf")
            for router, value in self.cost_D.items():
                for interface, cost in value.items():
                    if (router[0]=='H'):
                        if(router == p.dst):
                            print()
                            print('***Found destination host: ' + router)
                            print()
                            outgoing_interface = interface
                            found = True
                    elif not found and (cost + self.rt_tbl_D[p.dst][router]) < check_val:
                        print()
                        print('***Found cheap path going towards destination host through ' + router)
                        print()
                        check_val = value[interface] + self.rt_tbl_D[p.dst][router]
                        outgoing_interface = interface

            
            self.intf_L[outgoing_interface].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                    (self, p, i, 1))
            print()
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        
        #create a routing table update packet
        p = NetworkPacket(0, 'control', str(self.rt_tbl_D))
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            print()
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            print()
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        
        # possibly send out routing updates
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        print()
        route_table = ast.literal_eval(p.data_S)
        update = False
        
        for dest in route_table:
            for router in route_table[dest]:
                if dest not in list(self.rt_tbl_D):
                    if router in list(self.rt_tbl_D):
                        cost_sum = route_table[dest][router] + self.rt_tbl_D[router][self.name]
                        update = True
                        self.rt_tbl_D.update({dest : {self.name : cost_sum}})
                    else:
                        update = True
                        self.rt_tbl_D.update({dest : {self.name : '~~'}})
                else:
                    if router not in list(self.rt_tbl_D[dest].keys()):
                        update = True
                        self.rt_tbl_D[dest].update(route_table[dest])
                    else:
                        if router in list(self.rt_tbl_D):
                            if route_table[dest][router] + self.rt_tbl_D[router][self.name] < self.rt_tbl_D[dest][self.name]:
                                update = True
                                self.rt_tbl_D[dest][self.name] = route_table[dest][router] + self.rt_tbl_D[router][self.name]
                                
                        if route_table[dest][router] < self.rt_tbl_D[dest][router]:
                            update = True
                            self.rt_tbl_D[dest][router] = route_table[dest][router]
        
        temp = {}
        for x in sorted(self.rt_tbl_D):
            temp[x] = self.rt_tbl_D[x]
        self.rt_tbl_D = temp
        
        if update:
            update_packet = NetworkPacket(0, 'control', str(self.rt_tbl_D))
            
            try:
                for interface in range(len(self.intf_L)):
                    self.intf_L[interface].put(update_packet.to_byte_S(), 'out', True)
            except queue.Full:
                print('Sorry... Queue was full')
                pass
             

    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
