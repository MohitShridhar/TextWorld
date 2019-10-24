# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT license.


# -*- coding: utf-8 -*-
import os
import re
import sys
import textwrap

from typing import Mapping, Union, Tuple, List

import numpy as np

from io import StringIO

import textworld
from textworld.core import GameState
from textworld.core import GameNotRunningError
from textworld.generator.game import Game, GameProgression
from textworld.generator.inform7 import Inform7Game



class TextWorldEnv(textworld.Environment):
    """
    Environment for playing games by TextWorld.
    """

    def load(self, gamefile: str) -> None:
        self._gamefile = gamefile
        self._game = textworld.Game.load(self._gamefile)
        self._game_progression = None
        self._inform7 = Inform7Game(self._game)

    def _gather_infos(self):
        self.state["game"] = self._game
        self.state["command_templates"] = self._game.command_templates
        self.state["verbs"] = self._game.verbs
        self.state["entities"] = self._game.entity_names
        self.state["objective"] = self._game.objective
        self.state["max_score"] = self._game.max_score

        for k, v in self._game.extras.items():
            self.state["extra.{}".format(k)] = v

        self.state["_game_progression"] = self._game_progression
        self.state["_facts"] = list(self._game_progression.state.facts)

        self.state["won"] = '*** The End ***' in self.state["feedback"]
        self.state["lost"] = '*** You lost! ***' in self.state["feedback"]

        self.state["_winning_policy"] = self._current_winning_policy
        if self.infos.policy_commands:
            self.state["policy_commands"] = []
            if self._game_progression.winning_policy is not None:
                self.state["policy_commands"] = self._inform7.gen_commands_from_actions(self._current_winning_policy)

        if self.infos.intermediate_reward:
            self.state["intermediate_reward"] = 0
            if self.state["won"]:
                # The last action led to winning the game.
                self.state["intermediate_reward"] = 1

            elif self.state["lost"]:
                # The last action led to losing the game.
                self.state["intermediate_reward"] = -1

            elif self._previous_winning_policy is None:
                self.state["intermediate_reward"] = 0

            else:
                diff = len(self._previous_winning_policy) - len(self._current_winning_policy)
                self.state["intermediate_reward"] = int(diff > 0) - int(diff < 0)  # Sign function.

        if self.infos.facts:
            self.state["facts"] = list(map(self._inform7.get_human_readable_fact, self.state["_facts"]))

        self.state["_last_action"] = self._last_action
        if self.infos.last_action and self._last_action is not None:
            self.state["last_action"] = self._inform7.get_human_readable_action(self._last_action)

        self.state["_valid_actions"] = self._game_progression.valid_actions
        self.state["_valid_commands"] = self._inform7.gen_commands_from_actions(self._game_progression.valid_actions)
        # To guarantee the order from one execution to another, we sort the commands.
        # Remove any potential duplicate commands (they would lead to the same result anyway).
        self.state["admissible_commands"] = sorted(set(self.state["_valid_commands"]))

        if self.infos.moves:
            self.state["moves"] = self._moves

    def reset(self):
        self.prev_state = None
        self.state = GameState()
        track_quests = (self.infos.intermediate_reward or self.infos.policy_commands)
        self._game_progression = GameProgression(self._game, track_quests=track_quests)
        self._last_action = None
        self._previous_winning_policy = None
        self._current_winning_policy = self._game_progression.winning_policy
        self._moves = 0

        self.state.raw = "" # TODO
        self.state.feedback = ""  # TODO
        self._gather_infos()
        return self.state

    def step(self, command: str):
        command = command.strip()
        self.prev_state = self.state

        self.state = GameState()
        self.state.last_command = command
        self.state.raw = "" # TODO
        self.state.feedback = ""  # TODO
        self._previous_winning_policy = self._current_winning_policy

        self._last_action = None
        try:
            # Find the action corresponding to the command.
            idx = self.prev_state["_valid_commands"].index(command)
            self._last_action = self._game_progression.valid_actions[idx]
            # An action that affects the state of the game.
            self._game_progression.update(self._last_action)
            self._current_winning_policy = self._game_progression.winning_policy
            self._moves += 1
        except ValueError:
            # print("Unknown command: {}".format(command))
            pass  # We assume nothing happened in the game.

        self._gather_infos()
        self.state["score"] = self._game_progression
        self.state["done"] = self.state["won"] or self.state["lost"]
        return self.state, self.state["score"], self.state["done"]

    def render(self, mode: str = "human") -> None:
        outfile = StringIO() if mode in ['ansi', "text"] else sys.stdout

        msg = self.state.feedback.rstrip() + "\n"
        if self.display_command_during_render and self.state.last_command is not None:
            msg = '> ' + self.state.last_command + "\n" + msg

        # Wrap each paragraph.
        if mode == "human":
            paragraphs = msg.split("\n")
            paragraphs = ["\n".join(textwrap.wrap(paragraph, width=80)) for paragraph in paragraphs]
            msg = "\n".join(paragraphs)

        outfile.write(msg + "\n")

        if mode == "text":
            outfile.seek(0)
            return outfile.read()

        if mode == 'ansi':
            return outfile
