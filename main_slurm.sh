#!/bin/bash
#SBATCH --job-name=ollama
#SBATCH --partition=gpu
#SBATCH --output=logs/slurm-%j_output.txt    # Standard output file (%j expands to jobID)
#SBATCH --error=logs/slurm-%j_error.txt      # Standard error file
#SBATCH --time=24:00:00           # Time limit (HH:MM:SS)
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=28
#SBATCH --mem=100567M      # Memory per node

###################################################
# Module Loading
module load ollama

# Set environmental variables
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_KEEP_ALIVE=5m
export OLLAMA_CONTEXT_LENGTH=16000


###################################################
start_time=$SECONDS
echo "============== Slurm Job Info =============="
echo " Job ID:           $SLURM_JOB_ID"
echo " Job Name:         ${SLURM_JOB_NAME:-N/A}"
echo " User:             ${SLURM_JOB_USER:-$USER} (${SLURM_JOB_ACCOUNT:-N/A})"
echo " Partition:        ${SLURM_JOB_PARTITION:-N/A} (${SLURM_JOB_NODELIST:-N/A})"
echo
echo " Submit Host:      ${SLURM_SUBMIT_HOST:-N/A}"
echo " Work Directory:   $(pwd)"
echo
echo " Allocated CPUs:   $SLURM_CPUS_ON_NODE"
echo " Allocated GPUs:   $SLURM_JOB_GPUS"
echo
echo " Start Time:     $(date +%T)"
echo "============================================"


###################################################
ollama serve > ollama.log 2>&1 & disown

TARGET_SCRIPT="$1"
if [[ -z "$TARGET_SCRIPT" ]]; then
	echo "Usage: sbatch $0 <python_script_path> [script_args...]"
	exit 1
fi
shift

python -u "$TARGET_SCRIPT" "$@"


###################################################
echo "============================================"
end_time=$SECONDS
echo " Finish Time:      $(date +%T)"
echo " Time Taken:       $((end_time - start_time)) seconds"