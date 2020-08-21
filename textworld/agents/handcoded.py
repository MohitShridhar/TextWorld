# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT license.

import os
import sys
import json
import string
import random
from textworld import Agent

sys.path.append(os.environ['ALFRED_ROOT'])
import gen.constants as constants

class HandCodedAgentTimeout(NameError):
    pass

class HandCodedAgentFailed(NameError):
    pass

class BasePolicy(object):

    # Object and affordance priors
    OBJECTS = constants.OBJECTS_SINGULAR
    OPENABLE_OBJECTS = [o.lower() for o in constants.OPENABLE_CLASS_LIST]
    VAL_RECEPTACLE_OBJECTS = dict((r.lower(), [o.lower() for o in objs]) for r, objs in constants.VAL_RECEPTACLE_OBJECTS.items())
    OBJECT_TO_VAL_RECEPTACLE = dict((o, list()) for o in OBJECTS)
    for o in constants.OBJECTS:
        for r, os in constants.VAL_RECEPTACLE_OBJECTS.items():
            if o in os:
                OBJECT_TO_VAL_RECEPTACLE[o.lower()].append(r.lower())

    def __init__(self, task_params, max_steps=100):
        self.max_steps = max_steps
        self.task_params = task_params
        self.subgoals = [
            {'action': "look", 'param': ""}
        ]
        # receptacle
        self.receptacles = {}
        self.visible_objects = {}
        self.obj_cls_to_receptacle_map = {}

        # state memory
        self.subgoal_idx = 0
        self.curr_recep = ""
        self.checked_inside_curr_recep = False
        self.receptacles_to_check = []
        self.inventory = []
        self.action_backlog = []
        self.steps = 0

    def get_hashed_objects_in_str(self, obs, special_char='_'):
        return [o.rstrip(".,") for o in obs.split() if special_char in o]

    def get_objects_and_classes(self, obs, special_char='_'):
        hashed_objects = self.get_hashed_objects_in_str(obs, special_char=special_char)
        return dict((o, o.split(special_char)[0]) for o in hashed_objects)

    def get_list_of_objects_of_class(self, obj_cls, obj_dict):
        return [name for name, cls in obj_dict.items() if cls == obj_cls]

    def get_next_subgoal(self):
        subgoal = self.subgoals[self.subgoal_idx]
        sub_action, sub_param = subgoal['action'], subgoal['param']
        objs_of_interest = self.get_list_of_objects_of_class(sub_param, self.visible_objects)
        return sub_action, sub_param, objs_of_interest

    def get_list_of_receptacles_to_search_for_object_cls(self, obj_cls):
        obj_found_in_receps = self.OBJECT_TO_VAL_RECEPTACLE[obj_cls]
        return [r_name for r_name, r_cls in self.receptacles.items() if r_cls in obj_found_in_receps]

    def is_receptacle_openable(self, recep):
        return recep and self.receptacles[recep] in self.OPENABLE_OBJECTS

    def act(self, obs):
        self.steps += 1

        # Timeout
        if self.steps > self.max_steps:
            raise HandCodedAgentTimeout()
        # Finished all subgoals but still didn't achieve the goal
        elif self.subgoal_idx >= len(self.subgoals):
            raise HandCodedAgentFailed()

        if "Welcome" in obs:  # intro text with receptacles
            self.receptacles = self.get_objects_and_classes(obs)
        else:
            # get the objects which are visible in the current frame
            self.visible_objects = self.get_objects_and_classes(obs)

            # keep track of where all the objects are
            for o_name, o_cls in self.visible_objects.items():
                self.obj_cls_to_receptacle_map[o_cls] = self.curr_recep

        # FIND
        sub_action, sub_param, objs_of_interest = self.get_next_subgoal()
        if sub_action == 'find':
            # done criteria
            if len(objs_of_interest) > 0:
                self.receptacles_to_check = []
                self.subgoal_idx += 1
            else:
                # saw the obj class somewhere before
                if sub_param in self.obj_cls_to_receptacle_map:
                    self.receptacles_to_check = [self.obj_cls_to_receptacle_map[sub_param]]
                # use heuristic to determine which receptacle to check
                elif len(self.receptacles_to_check) == 0:
                    self.receptacles_to_check = self.get_list_of_receptacles_to_search_for_object_cls(sub_param)

                    # still no idea where to look, then look at all receptacles
                    if len(self.receptacles_to_check) == 0:
                        self.receptacles_to_check = list(self.receptacles.keys())

                # open the current receptacle if you can
                if self.is_receptacle_openable(self.curr_recep) and not self.checked_inside_curr_recep:
                    self.checked_inside_curr_recep = True
                    self.action_backlog.append("close {}".format(self.curr_recep))
                    return "open {}".format(self.curr_recep)

                # go to next receptacle
                else:
                    if len(self.action_backlog) == 0:
                        receptacle_to_check = self.receptacles_to_check.pop()
                        self.curr_recep = str(receptacle_to_check)
                        self.checked_inside_curr_recep = False if self.is_receptacle_openable(self.curr_recep) else True
                        return "go to {}".format(receptacle_to_check)
                    else:
                        return self.action_backlog.pop()

        # TAKE
        sub_action, sub_param, objs_of_interest = self.get_next_subgoal()
        if sub_action == 'take':
            obj = random.choice(objs_of_interest)
            self.inventory.append(obj)
            self.subgoal_idx += 1
            return "take {} from {}".format(obj, self.curr_recep)

        # PUT
        sub_action, sub_param, objs_of_interest = self.get_next_subgoal()
        if sub_action == 'put':
            obj = self.inventory.pop()
            self.subgoal_idx += 1
            return "put {} in/on {}".format(obj, self.curr_recep)

        # USE
        sub_action, sub_param, objs_of_interest = self.get_next_subgoal()
        if sub_action == 'use':
            obj = random.choice(objs_of_interest)
            self.subgoal_idx += 1
            return "use {}".format(obj)


class PickAndPlaceSimplePolicy(BasePolicy):

    def __init__(self, task_params, max_steps=100):
        super().__init__(task_params, max_steps=max_steps)
        self.subgoals = [
            {'action': 'find', 'param': self.task_params['object_target']},
            {'action': 'take', 'param': self.task_params['object_target']},
            {'action': 'find', 'param': self.task_params['parent_target']},
            {'action': 'put',  'param': self.task_params['parent_target']}
        ]


class LookAtObjInLightPolicy(BasePolicy):

    def __init__(self, task_params, max_steps=100):
        super().__init__(task_params, max_steps=max_steps)
        self.subgoals = [
            {'action': 'find', 'param': self.task_params['object_target']},
            {'action': 'take', 'param': self.task_params['object_target']},
            {'action': 'find', 'param': self.task_params['toggle_target']},
            {'action': 'use',  'param': self.task_params['toggle_target']}
        ]


class HandCodedAgent(Agent):
    """ Agent that simply follows a list of commands. """

    def __init__(self, max_steps=100):
        self.max_steps = max_steps

    def get_task_policy(self, task_type):
        task_class_str = task_type.replace("_", " ").title().replace(" ", '') + "Policy"
        if task_class_str in globals():
            return globals()[task_class_str]
        else:
            raise Exception("Invalid Task Type: %s" % task_type)

    def reset(self, env, game="INVALID"):
        env.infos.admissible_commands = True
        env.display_command_during_render = True

        traj_data_file = os.path.join(os.path.dirname(game), 'traj_data.json')
        with open(traj_data_file, 'r') as f:
            traj_data = json.load(f)

        self.task_params = {**traj_data['pddl_params'],
                            'task_type': traj_data['task_type']}
        self.task_params = dict((k, v.lower() if v in constants.OBJECTS else v) for k, v in self.task_params.items())

        game_state = env.reset()
        policy_class = self.get_task_policy(self.task_params['task_type'])
        self.policy = policy_class(self.task_params, max_steps=self.max_steps)

    def act(self, game_state, reward, done):
        obs = game_state['feedback']
        action = self.policy.act(obs)

        return action
