import { query, Content } from '/lib/xp/content'
import { get as contextGet } from '/lib/xp/context'
import { connect } from '/lib/xp/node'

import { forceArray } from '/lib/app/util/collections'
import { isEmpty } from '/lib/app/util/objects'

interface ComponentDescribable {
	descriptor?: string
	config?: Record<string, Record<string, unknown>>
}

interface NodeComponent {
	type: string
	path: string
	layout?: ComponentDescribable
	part?: ComponentDescribable
	page?: ComponentDescribable
}

interface NodeContentData {
	components?: NodeComponent | NodeComponent[]
}

interface ComponentInfo {
	name: string
	path: string
	isPart: boolean
	isLayout: boolean
	isPage: boolean
	config: Record<string, unknown>
}

export function hasView(content: Content): boolean {
    if (content) {
        const pageSections = forceArray(content.page).filter(page => !isEmpty(page))
        const templates = query({
            count: 1,
            query: `data.supports='${content.type}'`,
            contentTypes: [
                'portal:page-template'
            ]
        })
        return ((pageSections.length > 0) || (templates.total > 0))
    }
    return false
}

export function getComponents(contentId: string): ComponentInfo[] {
    try {
        const context = contextGet()
        const repo = connect({
            repoId: context?.repository,
            branch: context?.branch,
            principals: ['role:system.admin']
        })
    
        const nodeData = (contentId && repo.get({ key: contentId })) as NodeContentData | null

        return nodeData
            ? forceArray(nodeData.components)
                .map(component => {
                    const componentType = component.type
					const componentObj = (component as unknown as Record<string, ComponentDescribable>)[componentType] || {}
					const componentDescriptor = componentObj.descriptor || ''
					const descriptorAppName = componentDescriptor
						.substring(0, componentDescriptor.indexOf(':'))
						.split('.').join('-')
					const descriptorComponentName = componentDescriptor
						.substring(componentDescriptor.indexOf(':') + 1)
						.split('.').join('-')
					const componentConfig = (componentObj.config?.[descriptorAppName]?.[descriptorComponentName]) as Record<string, unknown> | undefined

					const componentLayout = component.layout || {}
					const componentPart = component.part || {}
					const componentPage = component.page || {}
                    return {
                        name: componentLayout.descriptor || componentPart.descriptor || componentPage.descriptor,
                        path: component.path,
                        isPart: componentPart.descriptor != null,
                        isLayout: componentLayout.descriptor != null,
                        isPage: componentPage.descriptor != null,
						config: componentConfig ?? {}
                    }
                })
            : []
    } catch(err) {
        return []
    }
}
