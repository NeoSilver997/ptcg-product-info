# Manual Card Linking Server Configuration

## Image Path Configuration

The server now supports configurable image paths for serving Pokemon TCG card images.

### Default Configuration

By default, the server expects images to be served from:
- **Base URL**: `http://localhost:3333` (Next.js development server)
- **Path Prefix**: `/cards/`

### Custom Configuration

To use a different image server:

1. **Copy the example config:**
   ```bash
   cp config.example.js config.js
   ```

2. **Edit `config.js`:**
   ```javascript
   module.exports = {
       IMAGE_BASE_URL: 'https://your-image-server.com',
       IMAGE_PATH_PREFIX: '/images/cards/',
       // ... other settings
   };
   ```

3. **Or use environment variables:**
   ```bash
   IMAGE_BASE_URL=https://your-image-server.com npm start
   ```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `IMAGE_BASE_URL` | `http://localhost:3333` | Base URL of the image server |
| `IMAGE_PATH_PREFIX` | `/cards/` | Path prefix for card images |
| `PORT` | `3000` | Server port for the linking interface |
| `DATABASES.EVENT_DB` | `../ptcg_events.db` | Path to events database |
| `DATABASES.MAIN_DB` | `../../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db` | Path to main cards database |

### Environment Variables

You can also override configuration using environment variables:

```bash
# Set image server URL
export IMAGE_BASE_URL=https://my-image-server.com

# Set server port
export PORT=8080

# Start the server
node server.js
```

### Image URL Processing

The server automatically converts external image URLs to the configured local paths:

- **External URL**: `https://assets.example.com/cards/pikachu.jpg`
- **Configured URL**: `http://localhost:3333/cards/pikachu.jpg`

This ensures images are served from your configured image server while maintaining compatibility with existing database entries.