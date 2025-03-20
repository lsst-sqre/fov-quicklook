from quicklook.tileinfo import TileInfo
from quicklook.types import GeneratorPod, TileId


def select_primary_generator(ccd_generator_map: dict[str, GeneratorPod], tile_id: TileId) -> tuple[GeneratorPod, list[GeneratorPod]]:
    # Select primary generator and other generators for the tile
    ccd_names = TileInfo.of(tile_id.level, tile_id.i, tile_id.j).ccd_names
    generators = sorted(set(g for g in (ccd_generator_map.get(ccd_name) for ccd_name in ccd_names) if g), key=lambda g: (g.name, g.port))
    if len(generators) == 0:
        raise NoOverlappingGenerators(f'No overlapping generators for {tile_id}')
    primary = generators[hash(tile_id) % len(generators)]
    return primary, generators


class NoOverlappingGenerators(RuntimeError):
    pass
