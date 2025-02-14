import pyvista as pv
import os
import argparse
from glob import glob

import logging

logger = logging.getLogger(__name__)


def quad_vtk_to_png(vtk_path, png_path):
    # Load the VTK file
    mesh = pv.read(vtk_path)

    # Extract points and scalar data
    points = mesh.points
    if "VonMises" not in mesh.point_data:
        raise ValueError("Scalar field 'VonMises' not found in the VTK file.")
    scalars = mesh.point_data["VonMises"]

    # Create a point cloud
    point_cloud = pv.PolyData(points)
    point_cloud["VonMises"] = scalars

    # Create a plot
    plotter = pv.Plotter(off_screen=True, window_size=[800, 800])
    plotter.add_mesh(
        point_cloud,
        scalars="VonMises",
        cmap="rainbow",
        render_points_as_spheres=True,
        point_size=10.0,
    )
    plotter.view_xy()

    plotter.screenshot(png_path)


if __name__ == "__main__":

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument(
        "batch_path",
        type=str,
        help="path to a folder where we put all cases in this batch in",
    )
    args = p.parse_args()

    batch_apath = os.path.abspath(args.batch_path)
    if not os.path.isdir(batch_apath):
        raise RuntimeError(f"batch folder {batch_apath} doesn't exist")

    logging.basicConfig(
        handlers=[
            logging.FileHandler(os.path.join(batch_apath, "visualize.log")),
            logging.StreamHandler(),
        ],
        level=logging.INFO,
        format="[%(levelname)s][%(asctime)s]%(message)s",
    )

    # Find all case folders
    case_apaths = glob(os.path.join(batch_apath, "case_*"))
    case_apaths = [d for d in case_apaths if os.path.isdir(d)]
    case_apaths.sort(
        key=lambda case_path: int(os.path.basename(case_path).split("_")[-1])
    )

    for case_apath in case_apaths:
        results = glob(os.path.join(case_apath, "opt_*"))
        results = [d for d in results if os.path.isdir(d)]
        results.sort(
            key=lambda result_folder: int(
                os.path.basename(result_folder).split("_")[-1]
            )
        )

        if len(results) == 0:
            logger.warning(f"no result folder for case {case_apath}")
            continue

        result_folder = results[0]
        if len(results) > 1:
            logger.warning(
                f" {case_apath} contains multiple result folders, using {result_folder}"
            )

        # Find the latest quad vtk
        quad_vtk_apaths = glob(os.path.join(case_apath, result_folder, "quad_*.vtk"))
        quad_vtk_apaths.sort(
            key=lambda vtk_path: int(
                os.path.splitext(os.path.split(vtk_path)[1])[0].split("_")[1]
            )
        )
        latest_quad_vtk_apaths = quad_vtk_apaths[-1]
        vtk_name = os.path.splitext(os.path.basename(latest_quad_vtk_apaths))[0]
        case_name = os.path.basename(case_apath)
        png_path = os.path.join(batch_apath, f"{case_name}_{vtk_name}.png")
        quad_vtk_to_png(latest_quad_vtk_apaths, png_path)
