NUMERIC_ALLOWLIST = "0123456789"
ALPHABETICAL_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ALPHANUMERIC_ALLOWLIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ,;:.?!-'"

#(x1, y1, x2, y2) for 2560x1440 resolution
REGIONS = {
    "drafting" : {
        "left" : (791, 249, 1231, 689),
        "center" : (1270, 249, 1710, 689),
        "right" : (1748, 249, 2188, 689),
    },
    "gem_requirement": {
        "left" : (971, 772, 1187, 812),
        "center" : (1461, 772, 1675, 812),
        "right" : (1941, 772, 2177, 812)
    },
    "resources" : {
        "footprints" : (107, 35, 207, 115),
        "dice" : (1962, 35, 2062, 115),
        "keys" : (2115, 35, 2215, 115),
        "gems" : (2277, 35, 2377, 115),
        "coins" : (2430, 35, 2530, 115),
    },
    "commissary": {
        "item 1" : (258, 499, 644, 556),
        "item 2" : (258, 595, 644, 651),
        "item 3" : (258, 686, 644, 743),
        "item 4": (258, 791, 644, 848)
    },
    "kitchen": {
        "item 1" : (291, 504, 671, 591),
        "item 2" : (291, 589, 671, 676),
        "item 3" : (291, 669, 671, 743)
    },
    "laboratory" : {
        "causes" : [(643, 631, 1144, 727),
                    (643, 737, 1144, 844),
                    (643, 897, 1144, 993)],
        "effects" : [(1240, 629, 1741, 725),
                     (1240, 762, 1741, 858),
                     (1240, 898, 1741, 994)],
    },
    "other" : {
        "current_room" : (2150, 1290, 2525, 1360),
    }
}