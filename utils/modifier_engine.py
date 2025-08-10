"""
Modifier Engine Utility

Handles random selection of modifiers from categories to prevent topic collapse
in generated conversations.
"""

import json
import random
from typing import List, Dict, Any
from pathlib import Path


class ModifierEngine:
    def __init__(self):
        """Initialize the modifier engine."""
        pass
    
    def load_modifiers(self, modifier_file_path: str) -> Dict[str, Any]:
        """Load modifier definitions from JSON file."""
        try:
            with open(modifier_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('modifying_adjectives', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading modifiers from {modifier_file_path}: {e}")
    
    def select_random_from_spectrum(self, spectrum: List[str], count: int = 1) -> List[str]:
        """Select random modifiers from a spectrum."""
        if not spectrum:
            return []
        
        count = min(count, len(spectrum))
        return random.sample(spectrum, count)
    
    def select_random_from_category(
        self, 
        category: Dict[str, List[str]], 
        min_spectra: int = 2, 
        max_spectra: int = 3,
        modifiers_per_spectrum: int = 1
    ) -> List[str]:
        """
        Select random modifiers from a category.
        
        Args:
            category: Dictionary of spectrum_name -> list of modifiers
            min_spectra: Minimum number of spectra to select from
            max_spectra: Maximum number of spectra to select from  
            modifiers_per_spectrum: Number of modifiers to pick from each spectrum
            
        Returns:
            List of selected modifier strings
        """
        if not category:
            return []
        
        spectrum_names = list(category.keys())
        
        # Determine how many spectra to use
        num_spectra = random.randint(
            min_spectra, 
            min(max_spectra, len(spectrum_names))
        )
        
        # Select random spectra
        selected_spectra = random.sample(spectrum_names, num_spectra)
        
        # Select modifiers from each spectrum
        selected_modifiers = []
        for spectrum_name in selected_spectra:
            spectrum = category[spectrum_name]
            modifiers = self.select_random_from_spectrum(spectrum, modifiers_per_spectrum)
            selected_modifiers.extend(modifiers)
        
        return selected_modifiers
    
    def generate_random_modifiers(
        self, 
        modifier_file_path: str, 
        requested_categories: List[str],
        min_spectra: int = 2,
        max_spectra: int = 3
    ) -> List[str]:
        """
        Generate random modifiers from requested categories.
        
        Args:
            modifier_file_path: Path to modifiers JSON file
            requested_categories: List of category names to select from
            min_spectra: Minimum spectra per category
            max_spectra: Maximum spectra per category
            
        Returns:
            List of selected modifier strings
        """
        modifiers = self.load_modifiers(modifier_file_path)
        all_selected_modifiers = []
        
        for category_name in requested_categories:
            if category_name not in modifiers:
                print(f"Warning: Category '{category_name}' not found in modifiers file")
                continue
            
            category = modifiers[category_name]
            category_modifiers = self.select_random_from_category(
                category, min_spectra, max_spectra
            )
            all_selected_modifiers.extend(category_modifiers)
        
        return all_selected_modifiers
    
    def get_available_categories(self, modifier_file_path: str) -> List[str]:
        """Get list of available modifier categories."""
        modifiers = self.load_modifiers(modifier_file_path)
        return list(modifiers.keys())
    
    def get_category_info(self, modifier_file_path: str, category_name: str) -> Dict[str, Any]:
        """Get information about a specific category."""
        modifiers = self.load_modifiers(modifier_file_path)
        
        if category_name not in modifiers:
            return {}
        
        category = modifiers[category_name]
        return {
            'spectra_count': len(category),
            'spectra_names': list(category.keys()),
            'total_modifiers': sum(len(spectrum) for spectrum in category.values()),
            'modifiers_per_spectrum': {
                spectrum_name: len(spectrum) 
                for spectrum_name, spectrum in category.items()
            }
        }