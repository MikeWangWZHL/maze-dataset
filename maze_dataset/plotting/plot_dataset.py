import matplotlib.pyplot as plt  # type: ignore[import]

from maze_dataset.dataset.maze_dataset import MazeDataset


def plot_dataset_mazes(ds: MazeDataset, count: int | None = None) -> tuple:
    count = count or len(ds)
    if count == 0:
        print(f"No mazes to plot for dataset")
        return
    fig, axes = plt.subplots(1, count, figsize=(count, 2))
    if count == 1:
        axes = [axes]
    for i in range(count):
        axes[i].imshow(ds[i].as_pixels())
        # remove ticks
        axes[i].set_xticks([])
        axes[i].set_yticks([])

    # set title
    kwargs: dict = {
        "grid_n": ds.cfg.grid_n,
        # "n_mazes": ds.cfg.n_mazes,
        **ds.cfg.maze_ctor_kwargs,
    }
    fig.suptitle(
        f"{ds.cfg.to_fname()}\n{ds.cfg.maze_ctor.__name__}({', '.join(f'{k}={v}' for k, v in kwargs.items())})"
    )
    # tight layout
    fig.tight_layout()
    # remove whitespace between title and subplots
    fig.subplots_adjust(top=1.0)

    return fig, axes


def print_dataset_mazes(ds: MazeDataset, count: int | None = None):
    count = count or len(ds)
    if count == 0:
        print(f"No mazes to print for dataset")
        return
    for i in range(count):
        print(ds[i].as_ascii(), "\n\n-----\n")
