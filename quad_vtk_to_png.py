import pyvista as pv
import os
import argparse
from glob import glob
from tqdm import tqdm
import tarfile
from sys import platform

import logging

logger = logging.getLogger(__name__)

if platform != "darwin":
    pv.start_xvfb()
pv.OFF_SCREEN = True


def stress_quad_vtk_to_png(vtk_path, png_path):
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


def design_grid_vtk_to_png(vtk_path, png_path):
    # Load the VTK file
    mesh = pv.read(vtk_path)

    # Apply IsoVolume filter on 'phi_blueprint'
    filtered_mesh = mesh.extract_surface().clip_scalar(
        scalars="phi_blueprint", value=-1e5, invert=False
    )
    filtered_mesh = filtered_mesh.clip_scalar(
        scalars="phi_blueprint", value=0, invert=True
    )

    # Create a plotter
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(
        filtered_mesh,
        scalars="x",
        cmap="coolwarm",
        show_scalar_bar=True,
        scalar_bar_args={
            "outline": False,
            "fmt": "%.4f",
            "color": "black",
            "position_x": 0.2,
            "position_y": 0.02,
            "title_font_size": 35,
            "label_font_size": 35,
            "font_family": "courier",
        },
    )

    # Set up camera angle for better visualization
    plotter.view_xy()
    plotter.set_background("white")
    plotter.window_size = [1920, 1080]
    plotter.camera.zoom(1.7)

    # Save the screenshot
    plotter.screenshot(png_path)
    plotter.close()


def plot_all_final_designs(args):
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

    for case_apath in tqdm(case_apaths):
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

        result_folder = results[-1]
        if len(results) > 1:
            logger.warning(
                f" {case_apath} contains multiple result folders, using latest {result_folder}"
            )

        # Find the latest quad vtk
        if args.what == "stress":
            vtk_apaths = glob(os.path.join(case_apath, result_folder, "quad_*.vtk"))
        else:
            vtk_apaths = glob(os.path.join(case_apath, result_folder, "grid_*.vtk"))

        vtk_apaths.sort(
            key=lambda vtk_path: int(
                os.path.splitext(os.path.split(vtk_path)[1])[0].split("_")[1]
            )
        )
        latest_vtk_apaths = vtk_apaths[-1]
        vtk_name = os.path.splitext(os.path.basename(latest_vtk_apaths))[0]
        case_name = os.path.basename(case_apath)
        png_path = os.path.join(batch_apath, f"{case_name}_{vtk_name}.png")

        if args.what == "stress":
            stress_quad_vtk_to_png(latest_vtk_apaths, png_path)
        else:
            design_grid_vtk_to_png(latest_vtk_apaths, png_path)


def plot_progress_single_case(args):
    case_name = args.case
    batch_apath = os.path.abspath(args.batch_path)
    case_apath = os.path.join(batch_apath, case_name)

    if not os.path.isdir(case_apath):
        logging.warning(f"case path {case_apath} does not exist")

    results = glob(os.path.join(case_apath, "opt_*"))
    results = [d for d in results if os.path.isdir(d)]
    results.sort(
        key=lambda result_folder: int(os.path.basename(result_folder).split("_")[-1])
    )

    if len(results) == 0:
        logger.warning(f"no result folder for case {case_apath}")
        return

    result_folder = results[-1]
    if len(results) > 1:
        logger.warning(
            f" {case_apath} contains multiple result folders, using latest {result_folder}"
        )

    # Sort quad vtk
    if args.what == "stress":
        vtk_apaths = glob(os.path.join(case_apath, result_folder, "quad_*.vtk"))
    else:
        vtk_apaths = glob(os.path.join(case_apath, result_folder, "grid_*.vtk"))

    vtk_apaths.sort(
        key=lambda vtk_path: int(
            os.path.splitext(os.path.split(vtk_path)[1])[0].split("_")[1]
        )
    )

    progress_png_dir = os.path.join(batch_apath, f"progress_{case_name}")
    if not os.path.isdir(progress_png_dir):
        os.mkdir(progress_png_dir)

    num = args.progress_num
    step = args.progress_every
    if num < 0:
        num = len(vtk_apaths)
        step = 1

    for i in tqdm(range(num)):
        j = i * step
        vtk_apath = vtk_apaths[j]
        vtk_name = os.path.splitext(os.path.basename(vtk_apath))[0]
        png_path = os.path.join(progress_png_dir, f"{case_name}_{vtk_name}.png")
        if args.what == "stress":
            stress_quad_vtk_to_png(vtk_apath, png_path)
        else:
            design_grid_vtk_to_png(vtk_apath, png_path)

    logger.info(f"compressing {progress_png_dir}")
    with tarfile.open(f"{progress_png_dir}.tar", "w") as tar:
        tar.add(progress_png_dir, arcname=os.path.basename(progress_png_dir))


if __name__ == "__main__":

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument(
        "batch_path",
        type=str,
        help="path to a folder where we put all cases in this batch in",
    )
    p.add_argument("--what", default="stress", choices=["stress", "design"])
    p.add_argument("--case", default=None, type=str)
    p.add_argument("--progress-every", type=int, default=20)
    p.add_argument("--progress-num", type=int, default=-1)
    args = p.parse_args()

    if args.case is None:
        logger.info("Plotting all final designs")
        plot_all_final_designs(args)
    else:
        logger.info(f"Plotting the optimization progress for case {args.case}")
        plot_progress_single_case(args)
