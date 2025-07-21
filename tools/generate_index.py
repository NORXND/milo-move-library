#!/usr/bin/env python3
"""
Generate Index Script

This script generates search indexes for games, songs, and moves for use in a React app.
Creates optimized JSON indexes for fast searching and filtering.

Usage:
    python generate_index.py [output_directory]

Arguments:
    output_directory: Optional directory to save index files (default: ./indexes)
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
import hashlib


def get_file_hash(filepath):
    """Generate MD5 hash of a file for change detection."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def get_file_info(filepath):
    """Get file information including size and modification time."""
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash': get_file_hash(filepath)
        }
    except:
        return None


def scan_game_directory(game_path, game_name):
    """
    Scan a game directory for songs and moves.
    
    Args:
        game_path: Path to the game directory
        game_name: Name of the game (dc1, dc2, dc3, etc.)
    
    Returns:
        Dictionary with game data
    """
    game_data = {
        'name': game_name,
        'path': game_path,
        'songs': {},
        'total_songs': 0,
        'total_moves': 0,
        'last_updated': datetime.now().isoformat()
    }
    
    if not os.path.exists(game_path):
        return game_data
    
    # Scan for song directories
    for item in os.listdir(game_path):
        item_path = os.path.join(game_path, item)
        
        if os.path.isdir(item_path):
            song_data = scan_song_directory(item_path, item)
            if song_data['moves']:  # Only include songs that have moves
                game_data['songs'][item] = song_data
                game_data['total_songs'] += 1
                game_data['total_moves'] += len(song_data['moves'])
    
    return game_data


def scan_song_directory(song_path, song_name):
    """
    Scan a song directory for move files.
    
    Args:
        song_path: Path to the song directory
        song_name: Name of the song
    
    Returns:
        Dictionary with song data
    """
    song_data = {
        'name': song_name,
        'path': song_path,
        'moves': {},
        'move_count': 0,
        'file_types': set(),
        'total_size': 0
    }
    
    # Scan for move files
    for root, dirs, files in os.walk(song_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Get relative path from song directory
            rel_path = os.path.relpath(file_path, song_path)
            
            file_info = get_file_info(file_path)
            if file_info:
                song_data['moves'][rel_path] = {
                    'name': file,
                    'path': rel_path,
                    'full_path': file_path,
                    'extension': file_ext,
                    **file_info
                }
                song_data['file_types'].add(file_ext)
                song_data['total_size'] += file_info['size']
                song_data['move_count'] += 1
    
    # Convert set to list for JSON serialization
    song_data['file_types'] = sorted(list(song_data['file_types']))
    
    return song_data


def scan_midi_banks(midi_bank_path):
    """
    Scan MIDI bank directory.
    
    Args:
        midi_bank_path: Path to the midi_bank directory
    
    Returns:
        Dictionary with MIDI bank data
    """
    midi_data = {
        'path': midi_bank_path,
        'files': {},
        'total_files': 0,
        'total_size': 0,
        'file_types': set(),
        'last_updated': datetime.now().isoformat()
    }
    
    if not os.path.exists(midi_bank_path):
        return midi_data
    
    # Scan for MIDI files
    for root, dirs, files in os.walk(midi_bank_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Get relative path from midi_bank directory
            rel_path = os.path.relpath(file_path, midi_bank_path)
            
            file_info = get_file_info(file_path)
            if file_info:
                midi_data['files'][rel_path] = {
                    'name': file,
                    'path': rel_path,
                    'full_path': file_path,
                    'extension': file_ext,
                    **file_info
                }
                midi_data['file_types'].add(file_ext)
                midi_data['total_size'] += file_info['size']
                midi_data['total_files'] += 1
    
    # Convert set to list for JSON serialization
    midi_data['file_types'] = sorted(list(midi_data['file_types']))
    
    return midi_data


def create_search_index(games_data):
    """
    Create optimized search indexes for fast querying.
    
    Args:
        games_data: Dictionary with all games data
    
    Returns:
        Dictionary with search indexes
    """
    search_index = {
        'games': [],
        'songs': [],
        'moves': [],
        'file_types': set(),
        'games_by_name': {},
        'songs_by_name': {},
        'moves_by_name': {},
        'stats': {
            'total_games': 0,
            'total_songs': 0,
            'total_moves': 0,
            'total_size': 0
        }
    }
    
    for game_name, game_data in games_data.items():
        # Add game to index
        game_entry = {
            'name': game_name,
            'song_count': game_data['total_songs'],
            'move_count': game_data['total_moves']
        }
        search_index['games'].append(game_entry)
        search_index['games_by_name'][game_name] = game_entry
        search_index['stats']['total_games'] += 1
        
        for song_name, song_data in game_data['songs'].items():
            # Add song to index
            song_entry = {
                'name': song_name,
                'game': game_name,
                'move_count': song_data['move_count'],
                'size': song_data['total_size'],
                'file_types': song_data['file_types']
            }
            search_index['songs'].append(song_entry)
            search_index['songs_by_name'][f"{game_name}:{song_name}"] = song_entry
            search_index['stats']['total_songs'] += 1
            search_index['stats']['total_size'] += song_data['total_size']
            
            for move_path, move_data in song_data['moves'].items():
                # Add move to index
                move_entry = {
                    'name': move_data['name'],
                    'path': move_path,
                    'song': song_name,
                    'game': game_name,
                    'extension': move_data['extension'],
                    'size': move_data['size'],
                    'modified': move_data['modified']
                }
                search_index['moves'].append(move_entry)
                search_index['moves_by_name'][f"{game_name}:{song_name}:{move_data['name']}"] = move_entry
                search_index['stats']['total_moves'] += 1
                search_index['file_types'].add(move_data['extension'])
    
    # Convert set to list for JSON serialization
    search_index['file_types'] = sorted(list(search_index['file_types']))
    
    return search_index


def save_indexes(output_dir, games_data, midi_data, search_index):
    """
    Save all indexes to JSON files.
    
    Args:
        output_dir: Output directory for index files
        games_data: Complete games data
        midi_data: MIDI bank data
        search_index: Search optimization index
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save complete games index
    games_file = os.path.join(output_dir, 'games_index.json')
    with open(games_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, indent=2, ensure_ascii=False)
    print(f"Saved games index: {games_file}")
    
    # Save MIDI banks index (separate file)
    midi_file = os.path.join(output_dir, 'midi_index.json')
    with open(midi_file, 'w', encoding='utf-8') as f:
        json.dump(midi_data, f, indent=2, ensure_ascii=False)
    print(f"Saved MIDI index: {midi_file}")
    
    # Save search index
    search_file = os.path.join(output_dir, 'search_index.json')
    with open(search_file, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, indent=2, ensure_ascii=False)
    print(f"Saved search index: {search_file}")
    
    # Save compact versions for production (minified)
    games_compact_file = os.path.join(output_dir, 'games_index.min.json')
    with open(games_compact_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, separators=(',', ':'), ensure_ascii=False)
    
    midi_compact_file = os.path.join(output_dir, 'midi_index.min.json')
    with open(midi_compact_file, 'w', encoding='utf-8') as f:
        json.dump(midi_data, f, separators=(',', ':'), ensure_ascii=False)
    
    search_compact_file = os.path.join(output_dir, 'search_index.min.json')
    with open(search_compact_file, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, separators=(',', ':'), ensure_ascii=False)
    
    print(f"Saved compact versions (.min.json files)")


def main():
    """Main function to generate all indexes."""
    # Get output directory from command line or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else './indexes'
    
    # Get the workspace root (parent of tools directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    
    print("Milo Move Library Index Generator")
    print("=" * 50)
    print(f"Workspace: {workspace_root}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Game directories to scan (excluding barks and tools)
    game_dirs = ['dc1', 'dc1_dlc', 'dc2', 'dc2_dlc', 'dc3', 'dc3_dlc', 'dcs']
    games_data = {}
    
    # Scan each game directory
    for game_name in game_dirs:
        game_path = os.path.join(workspace_root, game_name)
        print(f"Scanning {game_name}...")
        
        game_data = scan_game_directory(game_path, game_name)
        games_data[game_name] = game_data
        
        print(f"  Found {game_data['total_songs']} songs with {game_data['total_moves']} moves")
    
    # Scan MIDI banks
    print("\nScanning MIDI banks...")
    midi_bank_path = os.path.join(workspace_root, 'midi_bank')
    midi_data = scan_midi_banks(midi_bank_path)
    print(f"  Found {midi_data['total_files']} MIDI files")
    
    # Create search indexes
    print("\nCreating search indexes...")
    search_index = create_search_index(games_data)
    
    # Save all indexes
    print(f"\nSaving indexes to {output_dir}...")
    save_indexes(output_dir, games_data, midi_data, search_index)
    
    # Print summary
    print("\n" + "=" * 50)
    print("INDEX GENERATION COMPLETE")
    print("=" * 50)
    print(f"Total games: {search_index['stats']['total_games']}")
    print(f"Total songs: {search_index['stats']['total_songs']}")
    print(f"Total moves: {search_index['stats']['total_moves']}")
    print(f"Total MIDI files: {midi_data['total_files']}")
    print(f"Total size: {search_index['stats']['total_size'] / (1024*1024):.2f} MB")
    print(f"File types found: {', '.join(search_index['file_types'])}")
    print()
    print("Index files created:")
    print("  - games_index.json (complete game/song/move data)")
    print("  - midi_index.json (MIDI bank data)")
    print("  - search_index.json (optimized for searching)")
    print("  - *.min.json (minified versions for production)")
    print()
    print("Ready for use in React app!")


if __name__ == "__main__":
    main()
