## Try it out

To play with it locally, you can clone the repo and run the following commands:
```
touch mock_topo_executable && python sweep.py cfg_templates/case_lbracket_stress_min.cfg example.json batch_results --exe-path=./mock_topo_executable --dry-run
```


## The workflow

The basic idea of this workflow is as follows:
On local machine, a single optimization is executed by running

```
./topo case1.cfg
```

where
```
case1.cfg
```

is a collection of the configurations for the specific case. This is similar to passing options via command line arguments but more compact.
If you want to run this single job on PACE, you need the following ```submit.sbatch``` file

```
#!/bin/bash
#SBATCH -J batch_run_a_name_0
#SBATCH --account=gts-gkennedy9-coda20
#SBATCH -N1 --ntasks-per-node=1
#SBATCH --mem-per-cpu=4G
#SBATCH -t 24:00:00
#SBATCH -q inferno
#SBATCH -o results/batch_run_a_name/case_0/Report-%j.out

srun --account=gts-gkennedy9-coda20 topo case1.cfg
```

And submit the job on PACE login node via:
```
sbatch submit.sbatch
```

Now, if you want to run a parametric sweep on PACE, manually, over one or more options defined in the cfg file,  you need to create a list of submit_case_x.sbatch files, together with a config case_x.cfg , and execute the sbatch files as follows:

```
sbatch submit_case_1.sbatch
sbatch submit_case_2.sbatch
sbatch submit_case_3.sbatch
sbatch submit_case_4.sbatch
...
```

This manual process can very soon becomes cumbersome and error prone, if you want to repeated run batch cases over and over again. This is why I wrote this sweeper script that automates the config-editing and job submitting tasks.
