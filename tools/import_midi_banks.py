#!/usr/bin/env python3
"""
Import MIDI Banks Script

This script processes songs from .txt files in song_index directory and exports MIDI banks
using BoomyExporter.exe for each song.

Usage:
    python import_midi_banks.py <path_to_boomy_exporter> <input_folder> <game_name>

Arguments:
    path_to_boomy_exporter: Path to BoomyExporter.exe (or other executable)
    input_folder: Input folder containing song directories
    game_name: Game name (e.g., dc3, dc2, dc1, etc.)
"""

import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path


def run_boomy_export(exporter_path, input_folder, song_name, game_name, output_folder):
    """
    Run BoomyExporter.exe to export MIDI banks for a specific song.
    
    Args:
        exporter_path: Path to BoomyExporter.exe
        input_folder: Base input folder
        song_name: Name of the song
        game_name: Game name for origin
        output_folder: Temporary output folder
    """
    song_input_path = os.path.join(input_folder, song_name)
    
    # Check if song directory exists
    if not os.path.exists(song_input_path):
        print(f"Warning: Song directory '{song_input_path}' not found, skipping...")
        return False
    
    # Build the command
    cmd = [
        exporter_path,
        song_input_path,
        output_folder,
        "--midi",
        "--origin", game_name,
        "--name", song_name
    ]
    
    print(f"Exporting MIDI banks for '{song_name}'...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run the export command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Export successful for '{song_name}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error exporting '{song_name}': {e}")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error exporting '{song_name}': {e}")
        return False


def copy_midi_banks(tmp_folder, midi_bank_folder):
    """
    Copy MIDI bank files from temporary folder to midi_bank directory.
    Overrides existing files.
    
    Args:
        tmp_folder: Temporary folder containing exported files
        midi_bank_folder: Target midi_bank directory
    """
    midi_source_folder = os.path.join(tmp_folder, "midi_bank")
    
    if not os.path.exists(midi_source_folder):
        print(f"Warning: MIDI bank folder '{midi_source_folder}' does not exist")
        return False
    
    if not os.listdir(midi_source_folder):
        print(f"Warning: MIDI bank folder '{midi_source_folder}' is empty")
        return False
    
    try:
        # Create midi_bank folder if it doesn't exist
        os.makedirs(midi_bank_folder, exist_ok=True)
        
        # Copy all files from midi_bank to target folder (override existing)
        for item in os.listdir(midi_source_folder):
            src_path = os.path.join(midi_source_folder, item)
            dst_path = os.path.join(midi_bank_folder, item)
            
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"Copied directory (override): {item}")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"Copied file (override): {item}")
        
        return True
    except Exception as e:
        print(f"Error copying MIDI bank files: {e}")
        return False


def read_song_list(game_name):
    """
    Read song list from the corresponding .txt file in song_index directory.
    
    Args:
        game_name: Game name (e.g., dc3, dc2, dc1, etc.)
    
    Returns:
        List of song names
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    song_index_file = os.path.join(script_dir, "song_index", f"{game_name}.txt")
    
    if not os.path.exists(song_index_file):
        print(f"Error: Song index file '{song_index_file}' not found")
        return []
    
    try:
        with open(song_index_file, 'r', encoding='utf-8') as f:
            songs = [line.strip() for line in f.readlines() if line.strip()]
        
        print(f"Found {len(songs)} songs in '{song_index_file}'")
        return songs
    except Exception as e:
        print(f"Error reading song index file: {e}")
        return []


def main():
    """Main function to process all songs for MIDI bank export."""
    if len(sys.argv) != 4:
        print("Usage: python import_midi_banks.py <path_to_boomy_exporter> <input_folder> <game_name>")
        print("\nExample:")
        print("    python import_midi_banks.py BoomyExporter.exe D:\\songs dc3")
        sys.exit(1)
    
    exporter_path = sys.argv[1]
    input_folder = sys.argv[2]
    game_name = sys.argv[3]
    
    # Validate inputs
    if not os.path.exists(exporter_path):
        print(f"Error: BoomyExporter path '{exporter_path}' not found")
        sys.exit(1)
    
    if not os.path.exists(input_folder):
        print(f"Error: Input folder '{input_folder}' not found")
        sys.exit(1)
    
    # Get current working directory for midi_bank output
    cwd = os.getcwd()
    midi_bank_folder = os.path.join(cwd, "midi_bank")
    
    print(f"BoomyExporter: {exporter_path}")
    print(f"Input folder: {input_folder}")
    print(f"Game name: {game_name}")
    print(f"MIDI banks will be copied to: {midi_bank_folder}")
    print("-" * 50)
    
    # Read song list
    songs = read_song_list(game_name)
    if not songs:
        print("No songs found to process")
        sys.exit(1)
    
    successful_exports = 0
    total_songs = len(songs)
    
    # Process each song
    for i, song_name in enumerate(songs, 1):
        print(f"\nProcessing song {i}/{total_songs}: {song_name}")
        
        # Create temporary folder for this export
        with tempfile.TemporaryDirectory() as tmp_folder:
            print(f"Using temporary folder: {tmp_folder}")
            
            # Export MIDI banks using BoomyExporter
            if run_boomy_export(exporter_path, input_folder, song_name, game_name, tmp_folder):
                # Copy MIDI bank files to midi_bank directory (override existing)
                if copy_midi_banks(tmp_folder, midi_bank_folder):
                    successful_exports += 1
                    print(f"Successfully processed '{song_name}'")
                else:
                    print(f"Failed to copy MIDI banks for '{song_name}'")
            else:
                print(f"Failed to export '{song_name}'")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"MIDI Bank import completed!")
    print(f"Successfully processed: {successful_exports}/{total_songs} songs")
    print(f"MIDI banks directory: {midi_bank_folder}")
    
    if successful_exports < total_songs:
        sys.exit(1)


if __name__ == "__main__":
    main()
