import es 
import nn
import distrib 

import numpy as np 
import atari_py 
import gym 

import multiprocessing as mp 
import sys 
import time

env = gym.make('Pong-ram-v4') 

# print('Input:', env.reset().shape) 
# print('Output:', env.action_space) 

# for x in gym.envs.registry.all(): 
#     print(x) 

# sys.exit(0) 

x = i = nn.Input((128,)) 
x = nn.Dense(6)(x) 
net = nn.Model(i, x) 
del x, i 

outw, outs = nn.get_vectorized_weights(net) 

def fitness_pong(w, render: bool=False, steps=1000): 
    score = 0

    nn.set_vectorized_weights(net, w, outs) 

    for _ in range(3): 
        # env._max_episode_steps = steps
        obs = env.reset() 

        s = 0

        while True: 
            close = False

            if render: 
                close = not env.render()
                # print(obs) 

            obs = obs / 256 

            res = net.predict(np.expand_dims(obs, 0))[0]
            action = np.argmax(res) 

            obs, reward, done, _ = env.step(action)

            s += reward

            if done or close: 
                break

        score += s 

        if render: 
            print(s) 
        
        env.close() 

        if close: 
            break 

    return score / 3

if __name__ == "__main__": 
    e = es.EvolutionStrategy(
        outw, 
        5.0, 
        3000, 
        15, 
        min_sigma=1e-3, 
        big_sigma=5e-2, 
        wait_iter=100000
    )

    # pool = mp.Pool(processes=9) 
    pool = distrib.DistributedServer() 
    pool.start() 

    print("Waiting for connections...") 
    time.sleep(5) 
    print("Done!") 

    LENGTH = 1000
    times = 0 
    best = -float('inf') 

    try: 
        for i in range(1000): 
            scores = [] 
            pop = e.ask() 

            for ind in pop: 
                # scores.append(fitness_pong(ind, render=True, steps=LENGTH)) 
                # scores.append(pool.apply_async(fitness_pong, ((ind, False, LENGTH)))) 
                scores.append(pool.execute('pong_es', { 'w': ind })) 

            thread_scores = scores 
            scores = []

            ii = 0 
            for s in thread_scores: 
                scores.append(s.result())
                # scores.append(s.get())
                ii += 1 
                print("{} / {}".format(ii, len(thread_scores)), end='\r')

            # scores = [s.get() for s in scores] 

            e.tell(scores) 

            max_score = np.max(scores)  
            # if max_score > best: 
            if True: 
                if max_score > best: 
                    best = max_score 

                ind = pop[np.argmax(scores)] 
                # print(ind) 
                fitness_pong(ind, render=True) 

    except Exception as e: 
        print("Error while training:", e) 

    finally: 
        pool.stop() 