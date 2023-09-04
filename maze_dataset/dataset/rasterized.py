import typing

import numpy as np
import torch
from jaxtyping import Float, Int
from muutils.json_serialize import serializable_dataclass, serializable_field
from torch.utils.data import Dataset

from maze_dataset import MazeDataset, MazeDatasetConfig
from maze_dataset.maze import PixelColors, SolvedMaze
from maze_dataset.maze.lattice_maze import PixelGrid

_RIC_PADS: dict = {
    "left": ((1, 0), (0, 0)),
    "right": ((0, 1), (0, 0)),
    "up": ((0, 0), (1, 0)),
    "down": ((0, 0), (0, 1)),
}

# Define slices for each direction
_RIC_SLICES: dict = {
    "left": (slice(1, None), slice(None, None)),
    "right": (slice(None, -1), slice(None, None)),
    "up": (slice(None, None), slice(1, None)),
    "down": (slice(None, None), slice(None, -1)),
}


def _remove_isolated_cells(
    image: Int[np.ndarray, "RGB x y"]
) -> Int[np.ndarray, "RGB x y"]:
    """
    Removes isolated cells from an image. An isolated cell is a cell that is surrounded by walls on all sides.
    """
    masks: dict[str, np.ndarray] = {
        d: np.all(
            np.pad(
                image[_RIC_SLICES[d][0], _RIC_SLICES[d][1], :] == PixelColors.WALL,
                np.array((*_RIC_PADS[d], (0, 0)), dtype=np.int8),
                mode="constant",
                constant_values=True,
            ),
            axis=2,
        )
        for d in _RIC_SLICES.keys()
    }

    # Create a mask for non-wall cells
    mask_non_wall = np.all(image != PixelColors.WALL, axis=2)

    # print(f"{mask_non_wall.shape = }")
    # print(f"{ {k: masks[k].shape for k in masks.keys()} = }")

    # print(f"{mask_non_wall = }")
    # print(f"{masks['down'] = }")

    # Combine the masks
    mask = mask_non_wall & masks["left"] & masks["right"] & masks["up"] & masks["down"]

    # Apply the mask
    output_image = np.where(
        np.stack([mask] * 3, axis=-1),
        PixelColors.WALL,
        image,
    )

    return output_image


def _extend_pixels(
    image: Int[np.ndarray, "x y rgb"], n_mult: int = 2, n_bdry: int = 1
) -> Int[np.ndarray, "n_mult*x+2*n_bdry n_mult*y+2*n_bdry rgb"]:
    wall_fill: int = PixelColors.WALL[0]
    assert all(
        x == wall_fill for x in PixelColors.WALL
    ), "PixelColors.WALL must be a single value"

    output: np.ndarray = np.repeat(
        np.repeat(
            image,
            n_mult,
            axis=0,
        ),
        n_mult,
        axis=1,
    )

    # pad on all sides by n_bdry
    output = np.pad(
        output,
        pad_width=((n_bdry, n_bdry), (n_bdry, n_bdry), (0, 0)),
        mode="constant",
        constant_values=wall_fill,
    )

    return output


_RASTERIZED_CFG_ADDED_PARAMS: list[str] = [
    "remove_isolated_cells",
    "extend_pixels",
    "endpoints_as_open",
]


@serializable_dataclass
class RasterizedMazeDatasetConfig(MazeDatasetConfig):
    """
    - `remove_isolated_cells: bool` whether to set isolated cells to walls
    - `extend_pixels: bool` whether to extend pixels to match easy_2_hard dataset (2x2 cells, extra 1 pixel row of wall around maze)
    """

    remove_isolated_cells: bool = serializable_field(default=True)
    extend_pixels: bool = serializable_field(default=True)
    endpoints_as_open: bool = serializable_field(default=False)


class RasterizedMazeDataset(MazeDataset):
    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        # get the solved maze
        solved_maze: SolvedMaze = self.mazes[idx]

        # problem and solution mazes
        maze_pixels: PixelGrid = solved_maze.as_pixels(
            show_endpoints=True, show_solution=True
        )
        problem_maze: PixelGrid = maze_pixels.copy()
        solution_maze: PixelGrid = maze_pixels.copy()

        # in problem maze, set path to open
        problem_maze[(problem_maze == PixelColors.PATH).all(axis=-1)] = PixelColors.OPEN

        # wherever solution maze is PixelColors.OPEN, set it to PixelColors.WALL
        solution_maze[
            (solution_maze == PixelColors.OPEN).all(axis=-1)
        ] = PixelColors.WALL
        # wherever it is solution, set it to PixelColors.OPEN
        solution_maze[
            (solution_maze == PixelColors.PATH).all(axis=-1)
        ] = PixelColors.OPEN
        if self.cfg.endpoints_as_open:
            for color in (PixelColors.START, PixelColors.END):
                solution_maze[(solution_maze == color).all(axis=-1)] = PixelColors.OPEN

        # postprocess to match original easy_2_hard dataset
        if self.cfg.remove_isolated_cells:
            problem_maze = _remove_isolated_cells(problem_maze)
            solution_maze = _remove_isolated_cells(solution_maze)

        if self.cfg.extend_pixels:
            problem_maze = _extend_pixels(problem_maze)
            solution_maze = _extend_pixels(solution_maze)

        return torch.tensor([problem_maze, solution_maze])

    def get_batch(
        self, idxs: list[int] | None
    ) -> Float[torch.Tensor, "item in/tgt=2 x y rgb=3"]:
        if idxs is None:
            idxs = list(range(len(self)))
        batch: list[tuple[torch.Tensor, torch.Tensor]] = [self[i] for i in idxs]

        # return torch.stack([x[0] for x in batch]), torch.stack([x[1] for x in batch])
        return torch.cat(
            [
                torch.stack([x[0] for x in batch]),
                torch.stack([x[1] for x in batch]),
            ]
        )

    @classmethod
    def from_config_augmented(
        cls,
        cfg: RasterizedMazeDatasetConfig,
        **kwargs,
    ) -> Dataset:
        """loads either a maze transformer dataset or an easy_2_hard dataset"""
        _cfg_temp: MazeDatasetConfig = MazeDatasetConfig.load(cfg.serialize())
        return cls.from_base_MazeDataset(
            cls.from_config(cfg=_cfg_temp, **kwargs),
            added_params={
                k: v
                for k, v in cfg.serialize().items()
                if k in _RASTERIZED_CFG_ADDED_PARAMS
            },
        )

    @classmethod
    def from_base_MazeDataset(
        cls,
        base_dataset: MazeDataset,
        added_params: dict | None = None,
    ) -> Dataset:
        """loads either a maze transformer dataset or an easy_2_hard dataset"""
        if added_params is None:
            added_params = dict(
                remove_isolated_cells=True,
                extend_pixels=True,
            )
        output: MazeDataset = cls(
            cfg=base_dataset.cfg,
            mazes=base_dataset.mazes,
        )
        cfg: RasterizedMazeDatasetConfig = RasterizedMazeDatasetConfig.load(
            {
                **base_dataset.cfg.serialize(),
                **added_params,
            }
        )
        output.cfg = cfg
        return output

    def plot(self, count: int | None = None, show: bool = True) -> tuple:
        import matplotlib.pyplot as plt

        print(f"{self[0][0].shape = }, {self[0][1].shape = }")
        count = count or len(self)
        if count == 0:
            print(f"No mazes to plot for dataset")
            return
        fig, axes = plt.subplots(2, count, figsize=(15, 5))
        if count == 1:
            axes = [axes]
        for i in range(count):
            axes[0, i].imshow(self[i][0])
            axes[1, i].imshow(self[i][1])
            # remove ticks
            axes[0, i].set_xticks([])
            axes[0, i].set_yticks([])
            axes[1, i].set_xticks([])
            axes[1, i].set_yticks([])

        if show:
            plt.show()

        return fig, axes


def make_numpy_collection(
    base_cfg: RasterizedMazeDatasetConfig,
    grid_sizes: list[int],
    from_config_kwargs: dict | None = None,
    verbose: bool = True,
    key_fmt: str = "{size}x{size}",
) -> dict[
    typing.Literal["configs", "arrays"],
    dict[str, RasterizedMazeDatasetConfig | np.ndarray],
]:
    """create a collection of configs and arrays for different grid sizes, in plain tensor form

    output is of structure:
    ```
    {
        "configs": {
            "<n>x<n>": RasterizedMazeDatasetConfig,
            ...
        },
        "arrays": {
            "<n>x<n>": np.ndarray,
            ...
        },
    }
    ```
    """

    if from_config_kwargs is None:
        from_config_kwargs = {}

    datasets: dict[int, RasterizedMazeDataset] = {}

    for size in grid_sizes:
        if verbose:
            print(f"Generating dataset for maze size {size}...")

        cfg_temp: RasterizedMazeDatasetConfig = RasterizedMazeDatasetConfig.load(
            base_cfg.serialize()
        )
        cfg_temp.grid_n = size

        datasets[size] = RasterizedMazeDataset.from_config_augmented(
            cfg=cfg_temp,
            **from_config_kwargs,
        )

    return dict(
        configs={
            key_fmt.format(size=size): dataset.cfg for size, dataset in datasets.items()
        },
        arrays={
            # get_batch(None) returns a single tensor of shape (n, 2, x, y, 3)
            key_fmt.format(size=size): dataset.get_batch(None).cpu().numpy()
            for size, dataset in datasets.items()
        },
    )