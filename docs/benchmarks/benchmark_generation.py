import random
import timeit

from tqdm import tqdm

from maze_dataset import LatticeMazeGenerators, MazeDataset, MazeDatasetConfig

_BASE_CFG_KWARGS: dict = dict(
    grid_n=None,
    n_mazes=None,
)

# benchmark configs, not including sizes
BENCHMARK_CONFIGS_BASE: list[dict] = [
    dict(
        name="bk-dfs",
        maze_ctor=LatticeMazeGenerators.gen_dfs,
        maze_ctor_kwargs=dict(),
    ),
    dict(
        name="bk-dfs_forkless",
        maze_ctor=LatticeMazeGenerators.gen_dfs,
        maze_ctor_kwargs=dict(do_forks=False),
    ),
    dict(
        name="bk-dfs_td_5",
        maze_ctor=LatticeMazeGenerators.gen_dfs,
        maze_ctor_kwargs=dict(max_tree_depth=5),
    ),
    dict(
        name="bk-dfs_td_10",
        maze_ctor=LatticeMazeGenerators.gen_dfs,
        maze_ctor_kwargs=dict(max_tree_depth=10),
    ),
    dict(
        name="bk-wilson",
        maze_ctor=LatticeMazeGenerators.gen_wilson,
        maze_ctor_kwargs=dict(),
    ),
    dict(
        name="bk-perc_0.0",
        maze_ctor=LatticeMazeGenerators.gen_percolation,
        maze_ctor_kwargs=dict(p=0.0),
    ),
    dict(
        name="bk-perc_0.1",
        maze_ctor=LatticeMazeGenerators.gen_percolation,
        maze_ctor_kwargs=dict(p=0.1),
    ),
    dict(
        name="bk-perc_0.5",
        maze_ctor=LatticeMazeGenerators.gen_percolation,
        maze_ctor_kwargs=dict(p=0.5),
    ),
    dict(
        name="bk-dfs_perc_0.0",
        maze_ctor=LatticeMazeGenerators.gen_dfs_percolation,
        maze_ctor_kwargs=dict(p=0.0),
    ),
    dict(
        name="bk-dfs_perc_0.1",
        maze_ctor=LatticeMazeGenerators.gen_dfs_percolation,
        maze_ctor_kwargs=dict(p=0.1),
    ),
    dict(
        name="bk-dfs_perc_0.5",
        maze_ctor=LatticeMazeGenerators.gen_dfs_percolation,
        maze_ctor_kwargs=dict(p=0.5),
    ),
]


_GENERATE_KWARGS: dict = dict(
    gen_parallel=False,
    pool_kwargs=None,
    verbose=False,
    # do_generate = True,
    # load_local = False,
    # save_local = False,
    # zanj = None,
    # do_download = False,
    # local_base_path = "INVALID",
    # except_on_config_mismatch = True,
    # verbose = False,
)


def time_generation(
    base_configs: list[dict],
    grid_n_vals: list[int],
    n_mazes_vals: list[int],
    trials: int = 10,
    verbose: bool = False,
) -> dict[str, float]:
    # assemble configs
    configs: list[MazeDatasetConfig] = list()

    for cfg in base_configs:
        for grid_n in grid_n_vals:
            for n_mazes in n_mazes_vals:
                configs.append(
                    MazeDatasetConfig(
                        **cfg,
                        grid_n=grid_n,
                        n_mazes=n_mazes,
                    )
                )

    # shuffle configs (in place) (otherwise progress bar is annoying)
    random.shuffle(configs)

    # time generation for each config
    times: list[dict] = list()
    idx: int = 0
    total: int = len(configs)
    for cfg in tqdm(
        configs,
        desc="Timing generation",
        unit="config",
        total=total,
        disable=verbose,
    ):
        if verbose:
            print(f"Timing generation for config {idx}/{total}\n{cfg}")

        t: float = (
            timeit.timeit(
                stmt=lambda: MazeDataset.generate(cfg, **_GENERATE_KWARGS),
                number=trials,
            )
            / trials
        )

        if verbose:
            print(f"avg time: {t:.3f} s")

        times.append(
            dict(
                cfg_name=cfg.name,
                grid_n=cfg.grid_n,
                n_mazes=cfg.n_mazes,
                maze_ctor=cfg.maze_ctor.__name__,
                maze_ctor_kwargs=cfg.maze_ctor_kwargs,
                trials=trials,
                time=t,
            )
        )
        
        idx += 1

    return times


def run_benchmark(
    save_path: str = "tests/_temp/benchmark_generation.jsonl",
    base_configs: list[dict] | None = None,
    grid_n_vals: list[int] = [2, 4, 8, 16, 32, 64],
    n_mazes_vals: list[int] = [1, 10, 100],
    trials: int = 10,
):
    import pandas as pd

    if base_configs is None:
        base_configs = BENCHMARK_CONFIGS_BASE

    times: list[dict] = time_generation(
        base_configs=base_configs,
        grid_n_vals=grid_n_vals,
        n_mazes_vals=n_mazes_vals,
        trials=trials,
        verbose=True,
    )

    df: pd.DataFrame = pd.DataFrame(times)

    # print the whole dataframe contents to console as csv
    print(df.to_csv())

    # save to file
    df.to_json(save_path, orient="records", lines=True)

    return df


if __name__ == "__main__":
    run_benchmark()
