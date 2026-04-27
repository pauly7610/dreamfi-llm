import type { ConsolePayload } from '../types/console'

import { InboxNewPage } from './InboxNewPage'

type ReviewPageProps = {
  data: ConsolePayload | null
}

function ReviewPage({ data }: ReviewPageProps) {
  return <InboxNewPage data={data} />
}

export default ReviewPage
