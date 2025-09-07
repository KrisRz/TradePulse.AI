#!/usr/bin/env node

/**
 * Fix Duplicate Icon Imports
 * Removes duplicate imports and unused variables
 */

const fs = require('fs');
const path = require('path');

function fixDuplicatesInFile(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    let modified = false;

    // Fix import statements with duplicates
    const importRegex = /import\s*\{([^}]+)\}\s*from\s*['"]lucide-preact['"];?/g;
    const matches = [...content.matchAll(importRegex)];
    
    if (matches.length > 0) {
      matches.forEach(match => {
        const imports = match[1]
          .split(',')
          .map(imp => imp.trim())
          .filter(imp => imp.length > 0);
        
        // Remove duplicates
        const uniqueImports = [...new Set(imports)];
        
        if (uniqueImports.length !== imports.length) {
          const newImport = `import { ${uniqueImports.join(', ')} } from 'lucide-preact';`;
          content = content.replace(match[0], newImport);
          modified = true;
        }
      });
    }

    // Remove unused import declarations (basic cleanup)
    const unusedPatterns = [
      /,\s*TrendingDown(?=\s*[,}])/g,
      /,\s*Calendar(?=\s*[,}])/g,
      /,\s*Eye(?=\s*[,}])/g,
      /,\s*Globe(?=\s*[,}])/g,
      /,\s*Target(?=\s*[,}])/g,
      /,\s*Zap(?=\s*[,}])/g,
      /,\s*useEffect(?=\s*[,}])/g,
    ];

    unusedPatterns.forEach(pattern => {
      const newContent = content.replace(pattern, '');
      if (newContent !== content) {
        content = newContent;
        modified = true;
      }
    });

    if (modified) {
      fs.writeFileSync(filePath, content);
      console.log(`✅ Fixed duplicates: ${path.basename(filePath)}`);
      return true;
    }
    return false;
  } catch (error) {
    console.error(`❌ Error fixing ${filePath}:`, error.message);
    return false;
  }
}

function findTsxFiles(dir) {
  const files = [];
  
  function traverse(currentDir) {
    const entries = fs.readdirSync(currentDir);
    
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry);
      const stat = fs.statSync(fullPath);
      
      if (stat.isDirectory() && !entry.startsWith('.') && entry !== 'node_modules') {
        traverse(fullPath);
      } else if (entry.endsWith('.tsx') || entry.endsWith('.ts')) {
        files.push(fullPath);
      }
    }
  }
  
  traverse(dir);
  return files;
}

async function main() {
  console.log('🔧 Fixing Duplicate Imports');
  console.log('===========================\n');

  const srcDir = path.join(__dirname, 'src');
  const files = findTsxFiles(srcDir);
  
  let fixedCount = 0;
  
  for (const file of files) {
    if (fixDuplicatesInFile(file)) {
      fixedCount++;
    }
  }

  console.log(`\n📊 Results:`);
  console.log(`✅ Fixed: ${fixedCount} files`);
}

main().catch(console.error);
