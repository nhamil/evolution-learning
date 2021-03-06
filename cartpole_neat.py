# Trains the cart pole problem using NEAT 

import neat 

import numpy as np 
import gym 

import multiprocessing as mp 
import sys 

env = gym.make('CartPole-v1') 

# run cart pole problem
def fitness_cartpole(net: neat.Network, render: bool=False, steps=1000): 
    score = 0
    
    for _ in range(3): 
        env._max_episode_steps = steps
        obs = env.reset() 
        net.clear() 

        # total reward (fitness score) 
        s = 0

        while True: 
            close = False

            if render: 
                close = not env.render()
                # print(obs) 

            # determine action to take 
            res = net.predict(obs)
            action = np.argmax(res) 

            obs, reward, done, _ = env.step(action)

            s += reward

            if done or close: 
                break

        score += s 

        if render: 
            print(s) 
            env.close() 

    return score / 3

if __name__ == "__main__": 
    # init NEAT 
    neat_args = {
        'n_pop': 50, 
        'max_species': 30, 
        'species_threshold': 1.0, 
        'survive_threshold': 0.5, 
        'clear_species': 15, 
        'prob_add_node': 0.01, 
        'prob_add_conn': 0.5, 
        'prob_replace_weight': 0.01, 
        'prob_mutate_weight': 0.5, 
        'prob_toggle_conn': 0.01, 
        'prob_replace_activation': 0.1, 
        'std_new': 1.0, 
        'std_mutate': 0.1, 
        'activations': ['sigmoid'], 
        'dist_weight': 0.4, 
        'dist_activation': 1.0, 
        'dist_disjoint': 1.0  
    }

    n = neat.Neat(4, 2, neat_args) 

    # pool = mp.Pool() 

    LENGTH = 10000
    times = 0 

    try: 
        for i in range(1000): 
            scores = [] 
            pop = n.ask() 

            # eval population 
            for ind in pop: 
                scores.append(fitness_cartpole(ind, steps=LENGTH)) 
                # scores.append(pool.apply_async(fitness_xor, ((ind,)))) 

            # scores = [s.get() for s in scores] 

            n.tell(scores) 

            max_score = np.max(scores)  

            # show best individual 
            ind = pop[np.argmax(scores)] 
            fitness_cartpole(ind, render=True) 

            # early stopping if solution is found 
            if max_score == LENGTH: 
                times += 1 
            else: 
                times = 0 

            if times == 5: 
                ind = pop[np.argmax(scores)] 
                print(ind) 
                break 

    except Exception as e: 
        print("Error while training:", e) 