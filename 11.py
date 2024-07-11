import os
import shutil

# Define the source directory containing .smali files
source_dir = 'C:/input'

# Define the destination directory where new folders will be created
destination_dir = 'C:/output'

# Get a list of all .smali files in the source directory
smali_files = [f for f in os.listdir(source_dir) if f.endswith('.smali')]

# Create the new folders and copy one file per folder
for i, smali_file in enumerate(smali_files):
    folder_name = f'new{i+1}'
    folder_path = os.path.join(destination_dir, folder_name)
    
    # Create the main folder
    os.makedirs(folder_path, exist_ok=True)
    
    # Create the 'apps' subfolder
    apps_folder_path = os.path.join(folder_path, 'apps')
    os.makedirs(apps_folder_path, exist_ok=True)
    
    # Copy the .smali file to the 'apps' subfolder
    shutil.copy(os.path.join(source_dir, smali_file), apps_folder_path)

print('Files have been successfully copied and folders created.')
