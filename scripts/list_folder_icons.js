const https = require('https');
https.get('https://unpkg.com/lucide-static@latest/icons/?meta', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const json = JSON.parse(data);
        const files = json.files.map(f => f.path.split('/').pop());
        const folderIcons = files.filter(m => m.includes('folder'));
        console.log(folderIcons.join('\n'));
    });
});
