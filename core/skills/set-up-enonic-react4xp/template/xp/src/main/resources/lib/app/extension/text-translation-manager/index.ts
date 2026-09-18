import { connect, RepoConnection } from '/lib/xp/node'
import { Content } from '/lib/xp/content'
import { get as repoGet } from '/lib/xp/repo'
import { sanitize } from '/lib/xp/common'
import { newCache } from '/lib/cache'

import { forceArray } from '/lib/app/util/collections'

interface TranslationEntry {
	key: string
	value: string
	status: boolean
}

let repoConnect: RepoConnection | null = null

const cache = newCache({})

export function getValue(key: string, site: Content, content: Content): string {
    try {
        initializeRepo()
        const contentInherit = forceArray(content && content.inherit)
        const isLocalize = contentInherit.indexOf('CONTENT') === -1
    
        const language = sanitize(isLocalize
            ? ((content && content.language) || (site && site.language)) 
            : (site && site.language))
    
        const cacheKey = `ttm-${site._id}-${language || 'no'}`

        const obj = cache.get(cacheKey, () => {
            const query = repoConnect.query({
                count: 1,
                query: `_path='/${site._id}/${language || 'no'}'`
            })

            const objId = query?.hits[0]?.id
            return (objId && repoConnect.get({ key: objId })) || {}
        }) as { data?: TranslationEntry | TranslationEntry[] }

        const translates = forceArray<TranslationEntry>(obj.data)
        const translate = translates.filter(t => t.status && (t.key === key))[0]

        return (translate && translate.value) || ''
    } catch (err) {
        return ''
    }
}

export function clearCache(): void {
    cache.clear()
}

function initializeRepo(): void {
    if (!repoConnect && repoGet('text-translation-manager')) {
        try {
            repoConnect = connect({
                repoId: 'text-translation-manager',
                branch: 'master',
                principals: ['role:system.admin']
            })
        } catch(err) {
            repoConnect = null
        }
    }
}
