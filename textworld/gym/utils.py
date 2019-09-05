from typing import List, Optional

from gym.envs.registration import register, registry

from textworld import EnvInfos


def register_games(gamefiles: List[str],
                   request_infos: Optional[EnvInfos] = None,
                   batch_size: int = 1,
                   max_episode_steps: int = 50,
                   name: str = "",
                   **kwargs) -> str:
    """ Make an environment that will cycle through a list of games.

    Arguments:
        gamefiles:
            Paths for the TextWorld games (`*.ulx` + `*.json`, `*.z[1-8]`).
        request_infos:
            For customizing the information returned by this environment
            (see
            :py:class:`textworld.EnvInfos <textworld.envs.wrappers.filter.EnvInfos>`
            for the list of available information).

            .. warning:: This is only supported for `*.ulx` games generated with TextWorld.
        batch_size:
            Number of games to play at the same time. Default 1.
        max_episode_steps:
            Terminate a game after that many steps.
        name:
            Name for the new environment, i.e. "tw-{name}-v0". By default,
            the returned env_id is "tw-v0".

    Returns:
        The corresponding gym-compatible env_id to use.

    Example:

        >>> from textworld.generator import make_game, compile_game
        >>> options = textworld.GameOptions()
        >>> options.seeds = 1234
        >>> game = make_game(options)
        >>> game.extras["more"] = "This is extra information."
        >>> gamefile = compile_game(game)
        <BLANKLINE>
        >>> import gym
        >>> import textworld.gym
        >>> from textworld import EnvInfos
        >>> request_infos = EnvInfos(description=True, inventory=True, extras=["more"])
        >>> env_id = textworld.gym.register_games([gamefile], request_infos)
        >>> env = gym.make(env_id)
        >>> ob, infos = env.reset()
        >>> print(infos["extra.more"])
        This is extra information.

    """
    env_id = "tw-{}-v0".format(name) if name else "tw-v0"

    # If env already registered, bump the version number.
    if env_id in registry.env_specs:
        base, _ = env_id.rsplit("-v", 1)
        versions = [int(env_id.rsplit("-v", 1)[-1]) for env_id in registry.env_specs if env_id.startswith(base)]
        env_id = "{}-v{}".format(base, max(versions) + 1)

    if batch_size == 1:
        register(
            id=env_id,
            entry_point='textworld.gym.envs:TextworldGymEnv',
            max_episode_steps=max_episode_steps,
            kwargs={
                'gamefiles': gamefiles,
                'request_infos': request_infos,
                **kwargs}
        )
    else:
        register(
            id=env_id,
            entry_point='textworld.gym.envs:TextworldBatchGymEnv',
            max_episode_steps=max_episode_steps,
            kwargs={
                'gamefiles': gamefiles,
                'batch_size': batch_size,
                'request_infos': request_infos,
                **kwargs}
        )
    return env_id


def register_game(gamefile: str,
                  request_infos: Optional[EnvInfos] = None,
                  batch_size: int = 1,
                  max_episode_steps: int = 50,
                  name: str = "",
                  **kwargs) -> str:
    """ Make an environment for a particular game.

    Arguments:
        gamefile:
            Path for the TextWorld game (`*.ulx` + `*.json`, `*.z[1-8]`).
        request_infos:
            For customizing the information returned by this environment
            (see
            :py:class:`textworld.EnvInfos <textworld.envs.wrappers.filter.EnvInfos>`
            for the list of available information).

            .. warning:: This is only supported for `*.ulx` games generated with TextWorld.
        batch_size:
            Number of games to play at the same time. Default 1.
        max_episode_steps:
            Terminate a game after that many steps.
        name:
            Name for the new environment, i.e. "tw-{name}-v0". By default,
            the returned env_id is "tw-v0".

    Returns:
        The corresponding gym-compatible env_id to use.

    Example:

        >>> from textworld.generator import make_game, compile_game
        >>> options = textworld.GameOptions()
        >>> options.seeds = 1234
        >>> game = make_game(options)
        >>> game.extras["more"] = "This is extra information."
        >>> gamefile = compile_game(game)
        <BLANKLINE>
        >>> import gym
        >>> import textworld.gym
        >>> from textworld import EnvInfos
        >>> request_infos = EnvInfos(description=True, inventory=True, extras=["more"])
        >>> env_id = textworld.gym.register_game(gamefile, request_infos)
        >>> env = gym.make(env_id)
        >>> ob, infos = env.reset()
        >>> print(infos["extra.more"])
        This is extra information.

    """
    return register_games([gamefile], request_infos, batch_size, max_episode_steps, name, **kwargs)
