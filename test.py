import unittest
from room import ShopRoom, PuzzleRoom, UtilityCloset, CoatCheck, SecretPassage, Door

class TestRoomFromDict(unittest.TestCase):
    
    def test_shoproom_from_dict_basic(self):
        """Test that ShopRoom.from_dict() correctly creates a ShopRoom with basic attributes"""
        
        test_data = {
            "name": "KITCHEN",
            "cost": 0,
            "type": ["SHOP"],
            "description": "A well-equipped kitchen",
            "additional_info": "Sells food items",
            "shape": "L",
            "doors": [
                {"orientation": "N", "locked": False, "is_security": False, "leads_to": "?"},
                {"orientation": "E", "locked": True, "is_security": False, "leads_to": "?"}
            ],
            "position": [2, 3],
            "rank": 6,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": True,
            "terminal": None,
            "items_for_sale": {
                "BREAD": 5,
                "CHEESE": 8,
                "WINE": 15
            }
        }
        
        shop_room = ShopRoom.from_dict(test_data)
        
        # Test basic Room attributes
        self.assertEqual(shop_room.name, "KITCHEN")
        self.assertEqual(shop_room.cost, 0)
        self.assertEqual(shop_room.type, ["SHOP"])
        self.assertEqual(shop_room.description, "A well-equipped kitchen")
        self.assertEqual(shop_room.shape, "L")
        self.assertEqual(shop_room.position, (2, 3))
        self.assertEqual(shop_room.rank, 6)
        self.assertEqual(shop_room.has_been_entered, True)
        
        # Test ShopRoom-specific attributes
        self.assertEqual(shop_room.items_for_sale, {
            "BREAD": 5,
            "CHEESE": 8,
            "WINE": 15
        })
        
        # Test doors are proper Door objects
        self.assertEqual(len(shop_room.doors), 2)
        self.assertIsInstance(shop_room.doors[0], Door)
        self.assertIsInstance(shop_room.doors[1], Door)
        self.assertEqual(shop_room.doors[0].orientation, "N")
        self.assertEqual(shop_room.doors[0].locked, False)
        self.assertEqual(shop_room.doors[1].orientation, "E")
        self.assertEqual(shop_room.doors[1].locked, True)
        
        # Test that it's actually a ShopRoom instance
        self.assertIsInstance(shop_room, ShopRoom)
    
    def test_puzzleroom_from_dict_basic(self):
        """Test that PuzzleRoom.from_dict() correctly creates a PuzzleRoom with basic attributes"""
        
        test_data = {
            "name": "PARLOR",
            "cost": 0,
            "type": ["PUZZLE"],
            "description": "A cozy lounge with puzzles",
            "additional_info": "Contains the parlor puzzle",
            "shape": "L",
            "doors": [
                {"orientation": "W", "locked": False, "is_security": False, "leads_to": "?"},
                {"orientation": "N", "locked": False, "is_security": False, "leads_to": "?"}
            ],
            "position": [1, 8],
            "rank": 1,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": False,
            "terminal": None,
            "has_been_solved": False
        }
        
        puzzle_room = PuzzleRoom.from_dict(test_data)
        
        # Test basic Room attributes
        self.assertEqual(puzzle_room.name, "PARLOR")
        self.assertEqual(puzzle_room.type, ["PUZZLE"])
        self.assertEqual(puzzle_room.has_been_entered, False)
        
        # Test PuzzleRoom-specific attributes
        self.assertEqual(puzzle_room.has_been_solved, False)
        
        # Test doors are proper Door objects
        self.assertEqual(len(puzzle_room.doors), 2)
        self.assertIsInstance(puzzle_room.doors[0], Door)
        self.assertIsInstance(puzzle_room.doors[1], Door)
        self.assertEqual(puzzle_room.doors[0].orientation, "W")
        self.assertEqual(puzzle_room.doors[1].orientation, "N")
        
        # Test that it's actually a PuzzleRoom instance
        self.assertIsInstance(puzzle_room, PuzzleRoom)
    
    def test_utilitycloset_from_dict_basic(self):
        """Test that UtilityCloset.from_dict() correctly creates a UtilityCloset with basic attributes"""
        
        test_data = {
            "name": "UTILITY CLOSET",
            "cost": 0,
            "type": ["UTILITY"],
            "description": "Contains various switches",
            "additional_info": "Controls different areas",
            "shape": "DEAD END",
            "doors": [
                {"orientation": "S", "locked": False, "is_security": False, "leads_to": "?"}
            ],
            "position": [4, 7],
            "rank": 2,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": True,
            "terminal": None,
            "keycard_entry_system_switch": True,
            "gymnasium_switch": True,
            "darkroom_switch": False,
            "garage_switch": False
        }
        
        utility_closet = UtilityCloset.from_dict(test_data)
        
        # Test basic Room attributes
        self.assertEqual(utility_closet.name, "UTILITY CLOSET")
        self.assertEqual(utility_closet.type, ["UTILITY"])
        self.assertEqual(utility_closet.has_been_entered, True)
        
        # Test UtilityCloset-specific attributes
        self.assertEqual(utility_closet.keycard_entry_system_switch, True)
        self.assertEqual(utility_closet.gymnasium_switch, True)
        self.assertEqual(utility_closet.darkroom_switch, False)
        self.assertEqual(utility_closet.garage_switch, False)
        
        # Test doors are proper Door objects
        self.assertEqual(len(utility_closet.doors), 1)
        self.assertIsInstance(utility_closet.doors[0], Door)
        self.assertEqual(utility_closet.doors[0].orientation, "S")
        
        # Test that it's actually a UtilityCloset instance
        self.assertIsInstance(utility_closet, UtilityCloset)
    
    def test_coatcheck_from_dict_basic(self):
        """Test that CoatCheck.from_dict() correctly creates a CoatCheck with basic attributes"""
        
        test_data = {
            "name": "COAT CHECK",
            "cost": 0,
            "type": ["SERVICE"],
            "description": "Store items here",
            "additional_info": "Cross-run storage",
            "shape": "DEAD END",
            "doors": [
                {"orientation": "E", "locked": False, "is_security": False, "leads_to": "?"}
            ],
            "position": [0, 4],
            "rank": 5,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": False,
            "terminal": None,
            "stored_item": "MAGNIFYING GLASS"
        }
        
        coat_check = CoatCheck.from_dict(test_data)
        
        # Test basic Room attributes
        self.assertEqual(coat_check.name, "COAT CHECK")
        self.assertEqual(coat_check.type, ["SERVICE"])
        self.assertEqual(coat_check.has_been_entered, False)
        
        # Test CoatCheck-specific attributes
        self.assertEqual(coat_check.stored_item, "MAGNIFYING GLASS")
        
        # Test doors are proper Door objects
        self.assertEqual(len(coat_check.doors), 1)
        self.assertIsInstance(coat_check.doors[0], Door)
        self.assertEqual(coat_check.doors[0].orientation, "E")
        
        # Test that it's actually a CoatCheck instance
        self.assertIsInstance(coat_check, CoatCheck)
    
    def test_secretpassage_from_dict_basic(self):
        """Test that SecretPassage.from_dict() correctly creates a SecretPassage with basic attributes"""
        
        test_data = {
            "name": "SECRET PASSAGE",
            "cost": 0,
            "type": ["SECRET"],
            "description": "A hidden passage",
            "additional_info": "Connects to other areas",
            "shape": "STRAIGHT",
            "doors": [
                {"orientation": "N", "locked": False, "is_security": False, "leads_to": "?"},
                {"orientation": "S", "locked": False, "is_security": False, "leads_to": "?"}
            ],
            "position": [2, 5],
            "rank": 4,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "RARE",
            "has_been_entered": False,
            "terminal": None,
            "has_been_used": False
        }
        
        secret_passage = SecretPassage.from_dict(test_data)
        
        # Test basic Room attributes
        self.assertEqual(secret_passage.name, "SECRET PASSAGE")
        self.assertEqual(secret_passage.type, ["SECRET"])
        self.assertEqual(secret_passage.rarity, "RARE")
        self.assertEqual(secret_passage.has_been_entered, False)
        
        # Test SecretPassage-specific attributes
        self.assertEqual(secret_passage.has_been_used, False)
        
        # Test doors are proper Door objects
        self.assertEqual(len(secret_passage.doors), 2)
        self.assertIsInstance(secret_passage.doors[0], Door)
        self.assertIsInstance(secret_passage.doors[1], Door)
        self.assertEqual(secret_passage.doors[0].orientation, "N")
        self.assertEqual(secret_passage.doors[1].orientation, "S")
        
        # Test that it's actually a SecretPassage instance
        self.assertIsInstance(secret_passage, SecretPassage)
    
    def test_shoproom_from_dict_empty_items(self):
        """Test ShopRoom.from_dict() with empty items_for_sale"""
        
        test_data = {
            "name": "SHOWROOM",
            "cost": 0,
            "type": ["SHOP"],
            "description": "Empty showroom",
            "additional_info": "",
            "shape": "T",
            "doors": [],
            "position": [1, 1],
            "rank": 8,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": False,
            "terminal": None,
            "items_for_sale": {}
        }
        
        shop_room = ShopRoom.from_dict(test_data)
        self.assertEqual(shop_room.items_for_sale, {})
        self.assertIsInstance(shop_room, ShopRoom)
    
    def test_shoproom_from_dict_missing_items(self):
        """Test ShopRoom.from_dict() when items_for_sale is missing from data"""
        
        test_data = {
            "name": "LOCKSMITH",
            "cost": 0,
            "type": ["SHOP"],
            "description": "Locksmith shop",
            "additional_info": "",
            "shape": "DEAD END",
            "doors": [{"orientation": "S", "locked": False, "is_security": False, "leads_to": "?"}],
            "position": [3, 5],
            "rank": 4,
            "trunks": 0,
            "dig_spots": 0,
            "rarity": "COMMON",
            "has_been_entered": False,
            "terminal": None
            # items_for_sale is missing
        }
        
        shop_room = ShopRoom.from_dict(test_data)
        self.assertEqual(shop_room.items_for_sale, {})  # Should default to empty dict
        self.assertIsInstance(shop_room, ShopRoom)

if __name__ == '__main__':
    unittest.main()