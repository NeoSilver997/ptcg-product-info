// Configuration for manual card linking server
// Copy this file to config.js and modify as needed

module.exports = {
    // Image server configuration
    // Default: http://localhost:3333 (Next.js dev server)
    IMAGE_BASE_URL: process.env.IMAGE_BASE_URL || 'http://localhost:3333',

    // Image path prefix on the image server
    IMAGE_PATH_PREFIX: '/cards/',

    // Server port
    PORT: process.env.PORT || 3000,

    // Database paths (relative to project root)
    DATABASES: {
        EVENT_DB: '../ptcg_events.db',
        MAIN_DB: '../../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db'
    }
};