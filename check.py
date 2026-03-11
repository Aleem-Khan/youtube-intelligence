with open('index.html', encoding='utf-8') as f:
    content = f.read()
print('File size:', len(content))
print('Has channel data:', 'GOLDEN' in content)
print('Timestamp:', content[content.find('Updated'):content.find('Updated')+30])