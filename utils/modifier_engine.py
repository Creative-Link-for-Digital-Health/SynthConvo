"""
Modifier Engine Utility

Handles intelligent selection of modifiers from categories with contradiction
avoidance, complementary combinations, and context-aware weighting to create
coherent personality profiles.
"""

import json
import random
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict


class ModifierEngine:
    def __init__(self):
        """Initialize the modifier engine."""
        self.loaded_modifiers = None
        self.application_rules = None
        self.modifier_file_path = None
        
    def load_modifiers(self, modifier_file_path: str) -> Dict[str, Any]:
        """Load modifier definitions from JSON file."""
        try:
            with open(modifier_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.modifier_file_path = modifier_file_path
            self.loaded_modifiers = data.get('modifying_adjectives', {})
            self.application_rules = data.get('modifier_application_rules', {})
            
            return self.loaded_modifiers
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading modifiers from {modifier_file_path}: {e}")
    
    def _extract_intensity_level(self, modifier: str) -> str:
        """Extract intensity level from modifier string."""
        intensity_markers = {
            'very': 'high',
            'extremely': 'very_high', 
            'completely': 'very_high',
            'intensely': 'very_high',
            'obsessively': 'very_high',
            'mildly': 'low',
            'slightly': 'low',
            'somewhat': 'low',
            'moderately': 'medium',
            'moderate': 'medium'
        }
        
        modifier_lower = modifier.lower()
        for marker, level in intensity_markers.items():
            if marker in modifier_lower:
                return level
        
        return 'medium'  # Default intensity
    
    def _get_base_trait(self, modifier: str) -> str:
        """Extract base trait from modifier, removing intensity words."""
        intensity_words = ['very', 'extremely', 'completely', 'intensely', 'obsessively', 
                          'mildly', 'slightly', 'somewhat', 'moderately', 'moderate']
        
        words = modifier.lower().split()
        filtered_words = [word for word in words if word not in intensity_words]
        return ' '.join(filtered_words)
    
    def _check_contradictions(self, selected_modifiers: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if selected modifiers contradict each other.
        
        Returns:
            (is_valid, conflicting_pairs)
        """
        if not self.application_rules or 'avoid_contradictions' not in self.application_rules:
            return True, []
        
        contradictions = self.application_rules['avoid_contradictions']
        conflicting_pairs = []
        
        # Create sets of base traits for faster lookup
        selected_bases = {self._get_base_trait(mod): mod for mod in selected_modifiers}
        
        for contradiction_pair in contradictions:
            trait1_base = self._get_base_trait(contradiction_pair[0])
            trait2_base = self._get_base_trait(contradiction_pair[1])
            
            if trait1_base in selected_bases and trait2_base in selected_bases:
                conflicting_pairs.append([
                    selected_bases[trait1_base], 
                    selected_bases[trait2_base]
                ])
        
        return len(conflicting_pairs) == 0, conflicting_pairs
    
    def _match_intensity_levels(self, modifiers: List[str]) -> bool:
        """
        Check if intensity levels are reasonably matched.
        
        Returns:
            True if intensity levels are coherent
        """
        if len(modifiers) <= 1:
            return True
        
        intensity_levels = [self._extract_intensity_level(mod) for mod in modifiers]
        intensity_scores = {
            'low': 1,
            'medium': 2, 
            'high': 3,
            'very_high': 4
        }
        
        scores = [intensity_scores.get(level, 2) for level in intensity_levels]
        
        # Check if the range is reasonable (not mixing very low with very high)
        min_score, max_score = min(scores), max(scores)
        return max_score - min_score <= 2  # Allow max 2-point spread
    
    def _find_complementary_combinations(self, available_modifiers: Dict[str, List[str]]) -> List[str]:
        """Find good combinations from application rules."""
        if not self.application_rules or 'complementary_combinations' not in self.application_rules:
            return []
        
        complementary_pairs = self.application_rules['complementary_combinations']
        available_flat = []
        for spectrum_modifiers in available_modifiers.values():
            available_flat.extend(spectrum_modifiers)
        
        # Create mapping of base traits to actual modifiers
        base_to_modifier = {}
        for modifier in available_flat:
            base_trait = self._get_base_trait(modifier)
            if base_trait not in base_to_modifier:
                base_to_modifier[base_trait] = []
            base_to_modifier[base_trait].append(modifier)
        
        # Look for complementary pairs
        found_combinations = []
        for pair in complementary_pairs:
            trait1_base = self._get_base_trait(pair[0])
            trait2_base = self._get_base_trait(pair[1])
            
            if trait1_base in base_to_modifier and trait2_base in base_to_modifier:
                # Pick random intensity versions of these traits
                modifier1 = random.choice(base_to_modifier[trait1_base])
                modifier2 = random.choice(base_to_modifier[trait2_base])
                found_combinations.extend([modifier1, modifier2])
                
                if len(found_combinations) >= 4:  # Limit to 2 pairs
                    break
        
        return found_combinations
    
    def _weight_categories_by_context(self, available_categories: List[str], context_type: Optional[str]) -> List[str]:
        """Weight category selection based on scenario context."""
        if not context_type or not self.application_rules:
            return available_categories
        
        contextual_weighting = self.application_rules.get('contextual_weighting', {})
        if context_type not in contextual_weighting:
            return available_categories
        
        preferred_categories = contextual_weighting[context_type]
        weighted_categories = []
        
        # Add preferred categories multiple times to increase selection probability
        for category in available_categories:
            if category in preferred_categories:
                weighted_categories.extend([category] * 3)  # 3x weight
            else:
                weighted_categories.append(category)
        
        return weighted_categories
    
    def _select_from_spectrum_with_intensity_preference(
        self, 
        spectrum: List[str], 
        count: int = 1,
        preferred_intensity: Optional[str] = None
    ) -> List[str]:
        """Select from spectrum with optional intensity preference."""
        if not spectrum:
            return []
        
        count = min(count, len(spectrum))
        
        if preferred_intensity:
            # Filter by preferred intensity first
            preferred_modifiers = [
                mod for mod in spectrum 
                if self._extract_intensity_level(mod) == preferred_intensity
            ]
            
            if preferred_modifiers:
                return random.sample(preferred_modifiers, min(count, len(preferred_modifiers)))
        
        # Fallback to random selection
        return random.sample(spectrum, count)
    
    def _select_coherent_modifiers(
        self, 
        available_categories: Dict[str, Dict[str, List[str]]], 
        target_count: int = 3,
        max_attempts: int = 50
    ) -> List[str]:
        """
        Select modifiers that form a coherent personality profile.
        
        Args:
            available_categories: Dict of category_name -> {spectrum_name -> [modifiers]}
            target_count: Target number of modifiers to select
            max_attempts: Maximum attempts to find valid combination
            
        Returns:
            List of coherent modifiers
        """
        best_modifiers = []
        best_score = -1
        
        for attempt in range(max_attempts):
            selected_modifiers = []
            
            # Try to use complementary combinations first
            if random.random() < 0.4:  # 40% chance to use complementary
                # Flatten available modifiers for complementary search
                all_available = {}
                for category in available_categories.values():
                    all_available.update(category)
                
                complementary = self._find_complementary_combinations(all_available)
                if complementary:
                    selected_modifiers.extend(complementary[:target_count])
            
            # Fill remaining slots with random selection
            while len(selected_modifiers) < target_count:
                # Select random category and spectrum
                category_name = random.choice(list(available_categories.keys()))
                category = available_categories[category_name]
                spectrum_name = random.choice(list(category.keys()))
                spectrum = category[spectrum_name]
                
                # Select modifier, avoiding duplicates
                available_modifiers = [mod for mod in spectrum if mod not in selected_modifiers]
                if available_modifiers:
                    selected_modifiers.append(random.choice(available_modifiers))
            
            # Evaluate this combination
            is_valid, conflicts = self._check_contradictions(selected_modifiers)
            intensity_coherent = self._match_intensity_levels(selected_modifiers)
            
            # Score this combination
            score = 0
            if is_valid:
                score += 10
            if intensity_coherent:
                score += 5
            
            # Bonus for diversity (different categories)
            unique_categories = len(set(self._get_category_for_modifier(mod, available_categories) 
                                      for mod in selected_modifiers))
            score += unique_categories * 2
            
            # Keep track of best combination
            if score > best_score:
                best_score = score
                best_modifiers = selected_modifiers[:]
            
            # If we found a perfect combination, use it
            if is_valid and intensity_coherent and unique_categories >= 2:
                break
        
        return best_modifiers[:target_count]
    
    def _get_category_for_modifier(self, modifier: str, available_categories: Dict[str, Dict[str, List[str]]]) -> str:
        """Find which category a modifier belongs to."""
        for category_name, category in available_categories.items():
            for spectrum_name, spectrum in category.items():
                if modifier in spectrum:
                    return category_name
        return "unknown"
    
    def generate_smart_modifiers(
        self, 
        modifier_file_path: str, 
        requested_categories: List[str],
        context_type: Optional[str] = None,
        personality_coherence: str = "balanced",
        target_count: int = 3
    ) -> List[str]:
        """
        Generate modifiers with smart application rules.
        
        Args:
            modifier_file_path: Path to modifiers JSON file
            requested_categories: List of category names to select from
            context_type: Context for weighting ("customer_service", "technical", etc.)
            personality_coherence: "low", "balanced", or "high" - affects contradiction checking
            target_count: Target number of modifiers to return
            
        Returns:
            List of intelligently selected modifiers
        """
        # Load modifiers if not already loaded or file changed
        if (self.loaded_modifiers is None or 
            self.modifier_file_path != modifier_file_path):
            self.load_modifiers(modifier_file_path)
        
        if not self.loaded_modifiers:
            return []
        
        # Weight categories by context
        weighted_categories = self._weight_categories_by_context(requested_categories, context_type)
        
        # Build available categories dict
        available_categories = {}
        for category_name in requested_categories:
            if category_name in self.loaded_modifiers:
                available_categories[category_name] = self.loaded_modifiers[category_name]
            else:
                print(f"Warning: Category '{category_name}' not found in modifiers file")
        
        if not available_categories:
            return []
        
        # Generate coherent modifier combination
        if personality_coherence == "high":
            # High coherence: stricter rules, more attempts
            selected_modifiers = self._select_coherent_modifiers(
                available_categories, target_count, max_attempts=100
            )
        elif personality_coherence == "low":
            # Low coherence: more random selection
            selected_modifiers = self._select_random_modifiers_simple(
                available_categories, target_count
            )
        else:  # balanced
            # Balanced: moderate coherence checking
            selected_modifiers = self._select_coherent_modifiers(
                available_categories, target_count, max_attempts=50
            )
        
        return selected_modifiers
    
    def _select_random_modifiers_simple(
        self, 
        available_categories: Dict[str, Dict[str, List[str]]], 
        target_count: int
    ) -> List[str]:
        """Simple random selection with basic contradiction avoidance."""
        selected_modifiers = []
        
        for _ in range(target_count * 3):  # More attempts than needed
            if len(selected_modifiers) >= target_count:
                break
            
            # Select random category and spectrum
            category_name = random.choice(list(available_categories.keys()))
            category = available_categories[category_name]
            spectrum_name = random.choice(list(category.keys()))
            spectrum = category[spectrum_name]
            
            # Select random modifier
            candidate = random.choice(spectrum)
            
            if candidate not in selected_modifiers:
                # Basic contradiction check
                test_modifiers = selected_modifiers + [candidate]
                is_valid, _ = self._check_contradictions(test_modifiers)
                
                if is_valid:
                    selected_modifiers.append(candidate)
        
        return selected_modifiers[:target_count]
    
    def generate_random_modifiers(
        self, 
        modifier_file_path: str, 
        requested_categories: List[str],
        min_spectra: int = 2,
        max_spectra: int = 3
    ) -> List[str]:
        """
        Legacy method for backward compatibility.
        Redirects to smart generation with balanced coherence.
        """
        target_count = random.randint(min_spectra, max_spectra)
        return self.generate_smart_modifiers(
            modifier_file_path,
            requested_categories,
            personality_coherence="balanced",
            target_count=target_count
        )
    
    def get_available_categories(self, modifier_file_path: str) -> List[str]:
        """Get list of available modifier categories."""
        if (self.loaded_modifiers is None or 
            self.modifier_file_path != modifier_file_path):
            self.load_modifiers(modifier_file_path)
        
        return list(self.loaded_modifiers.keys()) if self.loaded_modifiers else []
    
    def get_category_info(self, modifier_file_path: str, category_name: str) -> Dict[str, Any]:
        """Get information about a specific category."""
        if (self.loaded_modifiers is None or 
            self.modifier_file_path != modifier_file_path):
            self.load_modifiers(modifier_file_path)
        
        if not self.loaded_modifiers or category_name not in self.loaded_modifiers:
            return {}
        
        category = self.loaded_modifiers[category_name]
        return {
            'spectra_count': len(category),
            'spectra_names': list(category.keys()),
            'total_modifiers': sum(len(spectrum) for spectrum in category.values()),
            'modifiers_per_spectrum': {
                spectrum_name: len(spectrum) 
                for spectrum_name, spectrum in category.items()
            }
        }
    
    def validate_modifier_combination(self, modifiers: List[str]) -> Dict[str, Any]:
        """
        Validate a combination of modifiers and provide feedback.
        
        Returns:
            Dictionary with validation results and suggestions
        """
        if not self.loaded_modifiers:
            return {"error": "No modifiers loaded"}
        
        is_valid, conflicts = self._check_contradictions(modifiers)
        intensity_coherent = self._match_intensity_levels(modifiers)
        
        # Get intensity levels
        intensities = [self._extract_intensity_level(mod) for mod in modifiers]
        
        # Count categories represented
        all_categories = {}
        for category_name, category in self.loaded_modifiers.items():
            all_categories[category_name] = category
        
        represented_categories = set()
        for modifier in modifiers:
            category = self._get_category_for_modifier(modifier, {'all': all_categories})
            if category != "unknown":
                represented_categories.add(category)
        
        return {
            "is_valid": is_valid and intensity_coherent,
            "has_contradictions": not is_valid,
            "conflicting_pairs": conflicts if not is_valid else [],
            "intensity_coherent": intensity_coherent,
            "intensity_levels": intensities,
            "category_diversity": len(represented_categories),
            "represented_categories": list(represented_categories),
            "suggestions": self._generate_improvement_suggestions(
                modifiers, is_valid, intensity_coherent, represented_categories
            )
        }
    
    def _generate_improvement_suggestions(
        self, 
        modifiers: List[str], 
        is_valid: bool, 
        intensity_coherent: bool,
        represented_categories: Set[str]
    ) -> List[str]:
        """Generate suggestions for improving a modifier combination."""
        suggestions = []
        
        if not is_valid:
            suggestions.append("Remove contradictory modifiers or replace with compatible alternatives")
        
        if not intensity_coherent:
            suggestions.append("Balance intensity levels - avoid mixing very mild with very extreme traits")
        
        if len(represented_categories) < 2:
            suggestions.append("Add modifiers from different categories for more diverse personality")
        
        if len(modifiers) < 2:
            suggestions.append("Consider adding more modifiers for richer personality depth")
        elif len(modifiers) > 5:
            suggestions.append("Consider reducing number of modifiers to avoid overwhelming personality")
        
        return suggestions