/**
 * Complete game options configuration based on Empyrion wiki
 * Source: https://empyrion.fandom.com/wiki/Console_commands_gameoptions
 */

const GAME_OPTIONS_CONFIG = {
    // Structure Management
    structure: {
        title: "Structure Management",
        icon: "🏗️",
        options: {
            DecayTime: {
                name: "Decay Time",
                allowedValues: "number",
                exampleValue: 24,
                note: "Time after which player-built structures without a core or less than 10 blocks in volume get removed when not visited. Set to 0 to disable.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "hours"
            },
            WipeTime: {
                name: "Wipe Time",
                allowedValues: "number",
                exampleValue: 0,
                note: "Time after which any player-built structures get removed when not visited. Set to 0 to disable.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "hours"
            },
            ProtectTime: {
                name: "Protect Time",
                allowedValues: "number",
                exampleValue: 48,
                note: "Time during which structures are offline protected, in real-time hours.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "hours"
            },
            ProtectDelay: {
                name: "Protect Delay",
                allowedValues: "number",
                exampleValue: 300,
                note: "Delay until the offline protection is enabled, in real-time seconds.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "seconds"
            },
            MaxStructures: {
                name: "Max Structures",
                allowedValues: "range",
                allowedRange: [0, 255],
                exampleValue: 200,
                note: "Max number of structures per playfield. Defaults to and is limited to 255; reduce if you have performance problems.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            }
        }
    },

    // Anti-Grief Protection
    antigrief: {
        title: "Anti-Grief Protection",
        icon: "🛡️",
        options: {
            AntiGriefDistancePvE: {
                name: "Anti-Grief Distance (PvE)",
                allowedValues: "number",
                exampleValue: 30,
                note: "Distance (in meters) around a faction's base where no other faction's base can be built in PvE playfields. Set to 0 to disable.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "meters"
            },
            AntiGriefDistancePvP: {
                name: "Anti-Grief Distance (PvP)",
                allowedValues: "number",
                exampleValue: 300,
                note: "Distance (in meters) around a faction's base where no other faction's base can be built in PvP playfields. Set to 0 to disable.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "meters"
            },
            AntiGriefOresDistance: {
                name: "Anti-Grief Ores Distance",
                allowedValues: "number",
                exampleValue: 30,
                note: "Distance (in meters) around ore deposits where no other faction's base can be built. Set to 0 to disable.",
                validFor: ["Survival", "Creative", "SP", "MP"],
                unit: "meters"
            },
            AntiGriefOresZone: {
                name: "Anti-Grief Ores Zone",
                allowedValues: ["All", "PvE", "PvP"],
                exampleValue: "PvE",
                note: "Playfield type where the AntiGriefOresDistance is valid.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            }
        }
    },

    // Difficulty Settings
    difficulty: {
        title: "Difficulty Settings",
        icon: "⚔️",
        options: {
            DiffAmountOfOre: {
                name: "Amount of Ore",
                allowedValues: ["Rich", "Normal", "Poor"],
                exampleValue: "Normal",
                note: "Controls how much ore is available in deposits.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffAttackStrength: {
                name: "Attack Strength",
                allowedValues: ["Easy", "Normal", "Hard"],
                exampleValue: "Normal",
                note: "Controls the strength of enemy attacks.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffNumberOfDeposits: {
                name: "Number of Deposits",
                allowedValues: ["Plenty", "Normal", "Few"],
                exampleValue: "Normal",
                note: "Controls how many ore deposits are available.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffDronePresence: {
                name: "Drone Presence",
                allowedValues: ["High", "Normal", "Low", "false"],
                exampleValue: "Normal",
                note: "Controls the number of drones on planets.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffPlayerProgression: {
                name: "Player Progression",
                allowedValues: ["Faster", "Normal", "Slower"],
                exampleValue: "Normal",
                note: "Controls XP gain rate and progression speed.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffFoodConsumption: {
                name: "Food Consumption",
                allowedValues: ["High", "Normal", "Low"],
                exampleValue: "Normal",
                note: "Controls how quickly players consume food.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffOxygenConsumption: {
                name: "Oxygen Consumption",
                allowedValues: ["High", "Normal", "Low"],
                exampleValue: "Normal",
                note: "Controls how quickly players consume oxygen.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffRadiationTemperature: {
                name: "Radiation & Temperature",
                allowedValues: ["High", "Normal", "Low"],
                exampleValue: "Normal",
                note: "Controls the impact of temperature and radiation on players.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffDegradationSpeed: {
                name: "Degradation Speed",
                allowedValues: ["High", "Normal", "Low"],
                exampleValue: "Normal",
                note: "Controls how quickly items degrade over time.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffBpProdTime: {
                name: "Blueprint Production Time",
                allowedValues: ["Slower", "Normal", "Faster"],
                exampleValue: "Normal",
                note: "Controls blueprint production speed in factories.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffConstrCraftTime: {
                name: "Construction & Crafting Time",
                allowedValues: ["Slower", "Normal", "Faster"],
                exampleValue: "Normal",
                note: "Controls construction and crafting speed.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffEscapePodContent: {
                name: "Escape Pod Content",
                allowedValues: ["Rich", "Medium", "Poor"],
                exampleValue: "Medium",
                note: "Controls the amount of starting resources in escape pods.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffPlayerBackpackDrop: {
                name: "Player Backpack Drop",
                allowedValues: ["DropAll", "DropToolbelt", "DropNothing"],
                exampleValue: "DropAll",
                note: "Controls what happens to player inventory when they die.",
                validFor: ["Survival", "SP", "MP"]
            },
            DiffDroneBaseAttack: {
                name: "Drone Base Attack",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Controls whether drones attack player bases.",
                validFor: ["Survival", "SP", "MP"]
            }
        }
    },

    // Game Features
    features: {
        title: "Game Features",
        icon: "⚙️",
        options: {
            EnableTrading: {
                name: "Enable Trading",
                allowedValues: ["All", "Player2System", "Player2Player", "System2Player", "None"],
                exampleValue: "All",
                note: "Controls what types of trading are enabled between players and NPCs.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            EnableCPUPoints: {
                name: "Enable CPU Points",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Enables the CPU points system for limiting ship complexity.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            EnableVolumeWeight: {
                name: "Enable Volume & Weight",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Enables realistic volume and weight restrictions for cargo.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            EnableMaxBlockCount: {
                name: "Enable Max Block Count",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Enables maximum block count limits for structures.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            AutoMinerDepletion: {
                name: "Auto Miner Depletion",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Controls whether auto miners deplete resource deposits over time.",
                validFor: ["Survival", "SP", "MP"]
            },
            RegeneratePOIs: {
                name: "Regenerate POIs",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Controls whether Points of Interest respawn after being destroyed.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            GroundedStructureSpawn: {
                name: "Grounded Structure Spawn",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Controls whether certain structures must be built on the ground.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            DespawnEscapePod: {
                name: "Despawn Escape Pod",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Controls whether escape pods despawn after use.",
                validFor: ["Survival", "SP", "MP"]
            },
            ForcePvP: {
                name: "Force PvP",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Forces PvP mode on all playfields regardless of their settings.",
                validFor: ["Survival", "MP"]
            },
            FriendlyFireInPvP: {
                name: "Friendly Fire in PvP",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Enables friendly fire between faction members in PvP areas.",
                validFor: ["Survival", "MP"]
            },
            OriginFactionStart: {
                name: "Origin Faction Start",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Enables faction selection at game start.",
                validFor: ["Survival", "SP", "MP"]
            },
            TurretUndergroundCheck: {
                name: "Turret Underground Check",
                allowedValues: ["true", "false"],
                exampleValue: "false",
                note: "Prevents turrets from targeting through terrain.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            },
            EnableDecoKnockDown: {
                name: "Enable Deco Knock Down",
                allowedValues: ["true", "false"],
                exampleValue: "true",
                note: "Allows decorative objects to be knocked down by explosions.",
                validFor: ["Survival", "Creative", "SP", "MP"]
            }
        }
    },

    // Advanced Options
    advanced: {
        title: "Advanced Options",
        icon: "🔧",
        options: {
            MaxSpawnedEnemies: {
                name: "Max Spawned Enemies",
                allowedValues: "number",
                exampleValue: 30,
                note: "Maximum number of enemies that can be spawned at once.",
                validFor: ["Survival", "SP", "MP"]
            }
        }
    }
};

// Helper functions for working with game options
const GameOptionsHelper = {
    /**
     * Get all available options across all categories
     */
    getAllOptions() {
        const allOptions = {};
        Object.values(GAME_OPTIONS_CONFIG).forEach(category => {
            Object.assign(allOptions, category.options);
        });
        return allOptions;
    },

    /**
     * Get option configuration by key
     */
    getOption(optionKey) {
        const allOptions = this.getAllOptions();
        return allOptions[optionKey] || null;
    },

    /**
     * Determine if a value is the default value for an option
     */
    isDefaultValue(optionKey, value) {
        const option = this.getOption(optionKey);
        if (!option) return false;
        
        // Handle different data types and comparison edge cases
        const defaultValue = option.exampleValue;
        
        // Direct equality check first
        if (defaultValue === value) return true;
        
        // Handle string/number conversions (e.g., "24" vs 24)
        if (String(defaultValue) === String(value)) return true;
        
        // Handle boolean string comparisons ("true"/"false" vs true/false)
        if (typeof defaultValue === 'boolean' && typeof value === 'string') {
            return defaultValue === (value.toLowerCase() === 'true');
        }
        if (typeof value === 'boolean' && typeof defaultValue === 'string') {
            return value === (defaultValue.toLowerCase() === 'true');
        }
        
        return false;
    },

    /**
     * Get the effective value for an option (scenario value or default)
     */
    getEffectiveValue(optionKey, scenarioOptions = {}) {
        const option = this.getOption(optionKey);
        if (!option) return null;

        // Check if option exists in scenario
        if (scenarioOptions.hasOwnProperty(optionKey)) {
            const scenarioValue = scenarioOptions[optionKey];
            const isActuallyDefault = this.isDefaultValue(optionKey, scenarioValue);
            
            return {
                value: scenarioValue,
                // Only mark as 'scenario' if it's actually different from default
                source: isActuallyDefault ? 'default' : 'scenario',
                isDefault: isActuallyDefault
            };
        }

        // Use default value (option is missing/commented out)
        return {
            value: option.exampleValue,
            source: 'default',
            isDefault: true
        };
    }
};