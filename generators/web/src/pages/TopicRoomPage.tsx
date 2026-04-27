import type { ConsolePayload } from '../types/console'

import { TopicNewPage } from './TopicNewPage'

type TopicRoomPageProps = {
  data: ConsolePayload | null
  topicId: string | null
}

function TopicRoomPage({ data, topicId }: TopicRoomPageProps) {
  return <TopicNewPage data={data} topicId={topicId} />
}

export default TopicRoomPage
