import pytest
import numpy as np

from maze_dataset import MazeDatasetConfig, LatticeMazeGenerators
from maze_dataset.dataset.maze_dataset import MazeDataset
from maze_dataset.dataset.rasterized import RasterizedMazeDataset, RasterizedMazeDatasetConfig, make_numpy_collection

_PARAMTETRIZATION = (
    "remove_isolated_cells, extend_pixels",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)


@pytest.mark.parametrize(*_PARAMTETRIZATION)
def test_rasterized_new(remove_isolated_cells, extend_pixels):
    cfg: RasterizedMazeDatasetConfig = RasterizedMazeDatasetConfig(
        name="test",
        grid_n=5,
        n_mazes=2,
        maze_ctor=LatticeMazeGenerators.gen_percolation, # use percolation here to get some isolated cells
        maze_ctor_kwargs=dict(p=0.4),
        remove_isolated_cells=remove_isolated_cells,
        extend_pixels=extend_pixels,
    )
    dataset: RasterizedMazeDataset = RasterizedMazeDataset.from_config_augmented(cfg, load_local=False)

    print(f"{dataset[0][0].shape = }, {dataset[0][1].shape = }")
    print(f"{dataset[0][1] = }\n{dataset[1][1] = }")


@pytest.mark.parametrize(*_PARAMTETRIZATION)
def test_rasterized_from_mazedataset(remove_isolated_cells, extend_pixels):
    cfg: MazeDatasetConfig = MazeDatasetConfig(
        name="test",
        grid_n=5,
        n_mazes=2,
        maze_ctor=LatticeMazeGenerators.gen_percolation, # use percolation here to get some isolated cells
        maze_ctor_kwargs=dict(p=0.4),
    )
    dataset_m: MazeDataset = MazeDataset.from_config(cfg, load_local=False)
    dataset_r: RasterizedMazeDataset = RasterizedMazeDataset.from_base_MazeDataset(
        dataset_m,
        added_params=dict(
            remove_isolated_cells=remove_isolated_cells,
            extend_pixels=extend_pixels,
        ),
    )

@pytest.mark.parametrize(*_PARAMTETRIZATION)
def test_make_numpy_collection(remove_isolated_cells, extend_pixels):
    cfg: RasterizedMazeDatasetConfig = RasterizedMazeDatasetConfig(
        name="test",
        grid_n=5,
        n_mazes=2,
        maze_ctor=LatticeMazeGenerators.gen_percolation, # use percolation here to get some isolated cells
        maze_ctor_kwargs=dict(p=0.4),
        remove_isolated_cells=remove_isolated_cells,
        extend_pixels=extend_pixels,
    )

    output = make_numpy_collection(
        base_cfg = cfg,
        grid_sizes = [2, 3],
        from_config_kwargs = dict(load_local=False),
        verbose = True,
    )

    assert isinstance(output, dict)
    assert isinstance(output["configs"], dict)
    assert isinstance(output["arrays"], dict)

    assert len(output["configs"]) == 2
    assert len(output["arrays"]) == 2

    for k, v in output["configs"].items():
        assert isinstance(k, str)
        assert isinstance(v, RasterizedMazeDatasetConfig)
    
    for k, v in output["arrays"].items():
        assert isinstance(k, str)
        assert isinstance(v, np.ndarray)