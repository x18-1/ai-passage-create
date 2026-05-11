export type ArticleContextOptions = {
  style?: string
  enabledImageMethods?: string[]
  enableMemory: boolean
  enableRag: boolean
  enabledSkillRefs: string[]
  ragCollections: string[]
}

export function buildCreateArticlePayload(topic: string, options: ArticleContextOptions) {
  return {
    topic,
    style: options.style || undefined,
    enabledImageMethods:
      options.enabledImageMethods && options.enabledImageMethods.length > 0
        ? options.enabledImageMethods
        : undefined,
    enableMemory: options.enableMemory,
    enableRag: options.enableRag,
    enabledSkillRefs: options.enabledSkillRefs,
    ragCollections: options.ragCollections,
  }
}
