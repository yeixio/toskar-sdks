// A TypeDoc plugin for the reference docs: leaves out the API's generated
// types (components, paths), which toskar.ai/developers/api documents
// route by route. Types that use them show them by name.
import { Converter } from 'typedoc'

export function load(app) {
  app.converter.on(Converter.EVENT_RESOLVE_BEGIN, (context) => {
    for (const name of ['components', 'paths']) {
      for (const r of context.project.getReflectionsByKind(0xffffffff)) {
        if (r.name === name && r.parent?.kindOf?.(1 | 2)) context.project.removeReflection(r)
      }
    }
  })
}
