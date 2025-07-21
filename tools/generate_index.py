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
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from functools import partial
import time


async def get_file_hash_async(filepath):
    """Generate MD5 hash of a file asynchronously."""
    try:
        async with aiofiles.open(filepath, 'rb') as f:
            content = await f.read()
            return hashlib.md5(content).hexdigest()
    except:
        return None


def get_file_hash_sync(filepath):
    """Generate MD5 hash of a file synchronously (for thread pool)."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def get_file_info_fast(filepath):
    """Get file information quickly without hash (for initial scan)."""
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash': None  # Will be filled later in parallel
        }
    except:
        return None


async def get_file_info_with_hash(filepath, executor):
    """Get complete file information including hash using thread pool."""
    try:
        stat = os.stat(filepath)
        # Run hash calculation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        hash_value = await loop.run_in_executor(executor, get_file_hash_sync, filepath)
        
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash': hash_value
        }
    except:
        return None


async def scan_game_directory_async(game_path, game_name, executor):
    """
    Scan a game directory for songs and moves asynchronously.
    
    Args:
        game_path: Path to the game directory
        game_name: Name of the game (dc1, dc2, dc3, etc.)
        executor: Thread pool executor for I/O operations
    
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
    
    # Get all directories first
    song_dirs = []
    for item in os.listdir(game_path):
        item_path = os.path.join(game_path, item)
        if os.path.isdir(item_path):
            song_dirs.append((item_path, item))
    
    # Process song directories in parallel
    song_tasks = []
    for item_path, item_name in song_dirs:
        task = scan_song_directory_async(item_path, item_name, executor)
        song_tasks.append((task, item_name))
    
    # Wait for all song scans to complete
    for task, song_name in song_tasks:
        song_data = await task
        if song_data['moves']:  # Only include songs that have moves
            game_data['songs'][song_name] = song_data
            game_data['total_songs'] += 1
            game_data['total_moves'] += song_data['move_count']
    return game_data


async def scan_song_directory_async(song_path, song_name, executor):
    """
    Scan a song directory for move folders asynchronously.
    
    Args:
        song_path: Path to the song directory
        song_name: Name of the song
        executor: Thread pool executor for I/O operations
    
    Returns:
        Dictionary with song data
    """
    song_data = {
        'name': song_name,
        'path': song_path,
        'moves': [],
        'move_count': 0,
        'last_updated': datetime.now().isoformat()
    }
    
    if not os.path.exists(song_path):
        return song_data
    
    # Scan for move directories (not files)
    for item in os.listdir(song_path):
        item_path = os.path.join(song_path, item)
        if os.path.isdir(item_path):
            # Add move folder name to the list
            song_data['moves'].append(item)
            song_data['move_count'] += 1
    
    # Sort moves alphabetically
    song_data['moves'].sort()
    
    return song_data


async def scan_midi_banks_async(midi_bank_path, executor):
    """
    Scan MIDI bank directory for folder names only asynchronously.
    
    Args:
        midi_bank_path: Path to the midi_bank directory
        executor: Thread pool executor for I/O operations
    
    Returns:
        Dictionary with MIDI bank data
    """
    midi_data = {
        'path': midi_bank_path,
        'sounds': [],
        'total_sounds': 0,
        'last_updated': datetime.now().isoformat()
    }
    
    if not os.path.exists(midi_bank_path):
        return midi_data
    
    # Scan for folder names only (direct child folders)
    for item in os.listdir(midi_bank_path):
        item_path = os.path.join(midi_bank_path, item)
        if os.path.isdir(item_path):
            # Add folder name to the list
            midi_data['sounds'].append(item)
            midi_data['total_sounds'] += 1
    
    # Sort sounds alphabetically
    midi_data['sounds'].sort()
    
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
        'games_by_name': {},
        'songs_by_name': {},
        'moves_by_name': {},
        'stats': {
            'total_games': 0,
            'total_songs': 0,
            'total_moves': 0
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
                'moves': song_data['moves']
            }
            search_index['songs'].append(song_entry)
            search_index['songs_by_name'][f"{game_name}:{song_name}"] = song_entry
            search_index['stats']['total_songs'] += 1
            
            for move_name in song_data['moves']:
                # Add move to index
                move_entry = {
                    'name': move_name,
                    'song': song_name,
                    'game': game_name
                }
                search_index['moves'].append(move_entry)
                search_index['moves_by_name'][f"{game_name}:{song_name}:{move_name}"] = move_entry
                search_index['stats']['total_moves'] += 1
    
    return search_index


async def save_indexes_async(output_dir, games_data, midi_data, search_index):
    """
    Save all indexes to JSON files asynchronously.
    
    Args:
        output_dir: Output directory for index files
        games_data: Complete games data (GAME->SONG->MOVE hierarchy)
        midi_data: MIDI bank data
        search_index: Search optimization index
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Moves index files (GAME->SONG->MOVE hierarchy)
    moves_file = os.path.join(output_dir, 'moves_index.json')
    moves_compact_file = os.path.join(output_dir, 'moves_index.min.json')
    
    async def write_moves_files():
        async with aiofiles.open(moves_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(games_data, indent=2, ensure_ascii=False))
        async with aiofiles.open(moves_compact_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(games_data, separators=(',', ':'), ensure_ascii=False))
        print(f"Saved moves index: {moves_file}")
    
    # MIDI index files
    midi_file = os.path.join(output_dir, 'midi_index.json')
    midi_compact_file = os.path.join(output_dir, 'midi_index.min.json')
    
    async def write_midi_files():
        async with aiofiles.open(midi_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(midi_data, indent=2, ensure_ascii=False))
        async with aiofiles.open(midi_compact_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(midi_data, separators=(',', ':'), ensure_ascii=False))
        print(f"Saved MIDI index: {midi_file}")
    
    # Search index files
    search_file = os.path.join(output_dir, 'search_index.json')
    search_compact_file = os.path.join(output_dir, 'search_index.min.json')
    
    async def write_search_files():
        async with aiofiles.open(search_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(search_index, indent=2, ensure_ascii=False))
        async with aiofiles.open(search_compact_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(search_index, separators=(',', ':'), ensure_ascii=False))
        print(f"Saved search index: {search_file}")
    
    # Run all write operations in parallel
    await asyncio.gather(
        write_moves_files(),
        write_midi_files(),
        write_search_files()
    )
    
    print(f"Saved compact versions (.min.json files)")


async def main_async():
    """Async main function to generate all indexes with parallel processing."""
    # Get output directory from command line or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else './indexes'
    
    # Get the workspace root (parent of tools directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    
    print("Milo Move Library Index Generator (Optimized)")
    print("=" * 50)
    print(f"Workspace: {workspace_root}")
    print(f"Output directory: {output_dir}")
    print()
    
    start_time = time.time()
    
    # Create thread pool executor for I/O operations
    max_workers = min(32, (os.cpu_count() or 1) + 4)  # Optimal for I/O bound tasks
    executor = ThreadPoolExecutor(max_workers=max_workers)
    
    try:
        # Game directories to scan (excluding barks and tools)
        game_dirs = ['dc1', 'dc1_dlc', 'dc2', 'dc2_dlc', 'dc3', 'dc3_dlc', 'dcs']
        
        # Create tasks for all game directory scans
        game_tasks = []
        for game_name in game_dirs:
            game_path = os.path.join(workspace_root, game_name)
            print(f"Starting scan of {game_name}...")
            task = scan_game_directory_async(game_path, game_name, executor)
            game_tasks.append((task, game_name))
        
        # Start MIDI bank scan in parallel
        print("Starting MIDI bank scan...")
        midi_bank_path = os.path.join(workspace_root, 'midi_bank')
        midi_task = scan_midi_banks_async(midi_bank_path, executor)
        
        # Wait for all game scans to complete
        games_data = {}
        for task, game_name in game_tasks:
            game_data = await task
            games_data[game_name] = game_data
            print(f"  ✓ {game_name}: {game_data['total_songs']} songs, {game_data['total_moves']} moves")
        
        # Wait for MIDI scan to complete
        midi_data = await midi_task
        print(f"  ✓ MIDI bank: {midi_data['total_sounds']} sounds")
        
        # Create search indexes (CPU bound, but relatively fast)
        print("\nCreating search indexes...")
        search_index = create_search_index(games_data)
        
    # Save all indexes in parallel
        print(f"\nSaving indexes to {output_dir}...")
        await save_indexes_async(output_dir, games_data, midi_data, search_index)
        
        elapsed_time = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 50)
        print("INDEX GENERATION COMPLETE")
        print("=" * 50)
        print(f"Total games: {search_index['stats']['total_games']}")
        print(f"Total songs: {search_index['stats']['total_songs']}")
        print(f"Total moves: {search_index['stats']['total_moves']}")
        print(f"Total MIDI sounds: {midi_data['total_sounds']}")
        print(f"Processing time: {elapsed_time:.2f} seconds")
        print(f"Thread pool workers: {max_workers}")
        print()
        print("Index files created:")
        print("  - moves_index.json (complete GAME->SONG->MOVE hierarchy)")
        print("  - midi_index.json (MIDI bank data)")
        print("  - search_index.json (optimized for searching)")
        print("  - *.min.json (minified versions for production)")
        print()
        print("Ready for use in React app!")
        
    finally:
        # Clean up thread pool
        executor.shutdown(wait=True)


def main():
    """Synchronous main function wrapper."""
    try:
        # Check if aiofiles is available
        import aiofiles
        # Run the async version
        asyncio.run(main_async())
    except ImportError:
        print("Warning: aiofiles not installed. Install it for better performance:")
        print("pip install aiofiles")
        print("Falling back to synchronous version...")
        # Fallback to synchronous version
        main_sync()


def main_sync():
    """Fallback synchronous main function."""
    # Get output directory from command line or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else './indexes'
    
    # Get the workspace root (parent of tools directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    
    print("Milo Move Library Index Generator (Sync Mode)")
    print("=" * 50)
    print(f"Workspace: {workspace_root}")
    print(f"Output directory: {output_dir}")
    print()
    
    start_time = time.time()
    
    # Game directories to scan (excluding barks and tools)
    game_dirs = ['dc1', 'dc1_dlc', 'dc2', 'dc2_dlc', 'dc3', 'dc3_dlc', 'dcs']
    games_data = {}
    
    # Use thread pool for parallel processing even in sync mode
    max_workers = min(16, (os.cpu_count() or 1) + 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Scan each game directory
        for game_name in game_dirs:
            game_path = os.path.join(workspace_root, game_name)
            print(f"Scanning {game_name}...")
            
            # Use async function but run it synchronously
            game_data = asyncio.run(scan_game_directory_async(game_path, game_name, executor))
            games_data[game_name] = game_data
            
            print(f"  Found {game_data['total_songs']} songs with {game_data['total_moves']} moves")
        
        # Scan MIDI banks
        print("\nScanning MIDI banks...")
        midi_bank_path = os.path.join(workspace_root, 'midi_bank')
        midi_data = asyncio.run(scan_midi_banks_async(midi_bank_path, executor))
        print(f"  Found {midi_data['total_sounds']} sounds")
    
    # Create search indexes
    print("\nCreating search indexes...")
    search_index = create_search_index(games_data)
    
    # Save all indexes (sync version)
    print(f"\nSaving indexes to {output_dir}...")
    save_indexes_sync(output_dir, games_data, midi_data, search_index)
    
    elapsed_time = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 50)
    print("INDEX GENERATION COMPLETE")
    print("=" * 50)
    print(f"Total games: {search_index['stats']['total_games']}")
    print(f"Total songs: {search_index['stats']['total_songs']}")
    print(f"Total moves: {search_index['stats']['total_moves']}")
    print(f"Total MIDI sounds: {midi_data['total_sounds']}")
    print(f"Processing time: {elapsed_time:.2f} seconds")
    print()
    print("Index files created:")
    print("  - moves_index.json (complete GAME->SONG->MOVE hierarchy)")
    print("  - midi_index.json (MIDI bank data)")
    print("  - search_index.json (optimized for searching)")
    print("  - *.min.json (minified versions for production)")
    print()
    print("Ready for use in React app!")


def save_indexes_sync(output_dir, games_data, midi_data, search_index):
    """
    Save all indexes to JSON files synchronously.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save moves index (GAME->SONG->MOVE hierarchy)
    moves_file = os.path.join(output_dir, 'moves_index.json')
    with open(moves_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, indent=2, ensure_ascii=False)
    print(f"Saved moves index: {moves_file}")
    
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
    moves_compact_file = os.path.join(output_dir, 'moves_index.min.json')
    with open(moves_compact_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, separators=(',', ':'), ensure_ascii=False)
    
    midi_compact_file = os.path.join(output_dir, 'midi_index.min.json')
    with open(midi_compact_file, 'w', encoding='utf-8') as f:
        json.dump(midi_data, f, separators=(',', ':'), ensure_ascii=False)
    
    search_compact_file = os.path.join(output_dir, 'search_index.min.json')
    with open(search_compact_file, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, separators=(',', ':'), ensure_ascii=False)
    
    print(f"Saved compact versions (.min.json files)")


if __name__ == "__main__":
    main()
