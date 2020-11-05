# import os 
# os.environ['OPENBLAS_NUM_THREADS'] = '1' 
# os.environ['MKL_NUM_THREADS'] = '1' 

import time 

import numpy as np 

from connect4 import Connect4
import distrib 
import nn 

def fitness_pi(data={}, shared={}): 
    x = data['x']
    out = np.array(np.square(np.pi - x[0]) + np.square(1.414 - x[1])) 
    return out 

def fitness_xor(data={}, shared={}): 
    model = data['model'] 
    model = nn.dict_to_network(model) 

    out = model.predict(np.array([
        [0, 0], 
        [0, 1], 
        [1, 0], 
        [1, 1]
    ])).reshape((4,))

    if 'print' in data and data['print']: 
        for y in out: 
            print("{:0.3f}".format(y))

    out[0] = 1 - out[0] 
    out[3] = 1 - out[3] 

    out = np.power(out, 0.5) 

    return np.array(4 - np.sum(out)) 

def fitness_connect4(data={}, shared={}): 
    total = 0 
    try: 
        for y in range(len(shared['models'])): 
            if data['x'] != y: 
                data['y'] = y 
                total += fitness_connect4_ind(data, shared) 
    except Exception as e: 
        print("Exception in fitness_connect4: {}".format(e))
        import traceback 
        traceback.print_exc() 
    return np.array(total) 

def fitness_connect4_ind(data={}, shared={}): 
    model_a = shared['models'][data['x']]
    model_a = nn.dict_to_network(model_a) 

    model_b = shared['models'][data['y']]
    model_b = nn.dict_to_network(model_b) 

    nets = { 1: model_a, -1: model_b }
    w, h = shared['size'] 

    env = Connect4(w, h) 

    p = False 
    if 'print' in data and data['print']: 
        p = True 

    while env.get_winner() is None: 
        state = env.get_state() 
        actions = env.get_actions() 
        player = env.get_player() 

        states = np.repeat(state[np.newaxis, :,:], len(actions), axis=0)
        for i in range(len(actions)): 
            env.step(actions[i], states[i])
        states = np.reshape(states, (len(actions), -1)) 

        values = np.reshape(nets[player].predict(states), (len(actions),)) 

        try: 
            env.step(actions[np.argmax(values)]) 
            if p: env.render() 
        except: 
            # print("Error while making move: {}".format(e))
            if p: print("{} won the game due to bad move by opponent".format('Y' if nets[player] == model_a else 'X'))
            if nets[player] == model_a: 
                return 0 
            else: 
                return 1 

    win = env.get_winner()
    if win == 0: 
        if p: print("X and Y tied")
        return 0 
    elif nets[win] == model_a: 
        if p: print("X won the game")
        return 1 
    else: 
        if p: print("Y won the game")
        return -1 
        


distrib.register_task("fitness_pi", fitness_pi) 
distrib.register_task("fitness_xor", fitness_xor) 
distrib.register_task("fitness_connect4", fitness_connect4) 

class EvolutionStrategy: 

    def __init__(self, x0, sigma0, n_pop, n_select): 
        self.x = np.array(x0, dtype=np.float) 
        self.sigma = np.full_like(x0, sigma0, dtype=np.float)  
        self.n_pop = n_pop 
        self.n_select = n_select 
        self.waiting = False 
        self.gen = 0 

    def ask(self): 
        if self.waiting: 
            raise Exception("A population has already been asked for") 

        self.waiting = True 
        self._pop = np.random.randn(self.n_pop, *self.x.shape) * self.sigma + self.x
        self.gen += 1
        return self._pop 

    def tell(self, scores): 
        if not self.waiting: 
            raise Exception("A population must be asked for") 

        self.waiting = False 
        inds_f = np.argsort(scores)[::-1]
        parents = self._pop[inds_f[:self.n_select]]

        print("Generation {}: best - {:0.3e}".format(self.gen, scores[inds_f[0]])) 

        self.sigma[:] = np.sqrt(np.mean(np.square(parents - self.x), axis=0)) + 1e-9
        self.x += np.mean(parents - self.x, axis=0)

if __name__ == "__main__": 
    CON4_WIDTH = 7 
    CON4_HEIGHT = 6 

    base = nn.ModelBuilder(CON4_WIDTH * CON4_HEIGHT) 
    base.dense(1) 
    base = base.build() 

    w = base.get_weights() 

    es = EvolutionStrategy(w[0], 10.0, 200, 10) 

    srv = distrib.DistributedServer() 
    try: 
        srv.start() 
        time.sleep(5) 

        shared = {} 
        scores = [] 

        for i in range(4): 
            pop = es.ask() 

            shared = { 
                'models': [nn.network_to_dict(base, (x, w[1])) for x in pop], 
                'size': (CON4_WIDTH, CON4_HEIGHT) 
            }
            srv.share(shared) 
            # time.sleep(5) 

            scores = [] 
            for x in range(len(pop)): 
                # scores.append(srv.execute('fitness_xor', {'model': nn.network_to_dict(base, (x, w[1]))})) 
                scores.append(srv.execute('fitness_connect4', {'x': x}))

            scores = [s.result() for s in scores] 
            # scores = [s.result() for s in scores] 
            es.tell(scores) 

            # if sorted(scores)[0] < 0.1: 
            #     break 

        best = np.argsort(scores)[::-1]
        print("Best 2 players: {} ({}), {} ({})".format(best[0], scores[best[0]], best[1], scores[best[1]]))

        # fitness_xor({'model': nn.network_to_dict(base, (es.x, w[1])), 'print': True})
        fitness_connect4_ind(data={'x': best[0], 'y': best[1], 'print': True}, shared=shared)
    
    finally: 
        srv.stop()
        pass 