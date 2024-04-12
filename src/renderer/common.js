
export class Summary {
    constructor(id, title, summary, entities) {
        this.id = id;
        this.title = title;
        this.summary = summary;
        this.entities = entities;
    }
}

export class Message {
    constructor(id, role, content) {
        this.id = id;
        this.role = role;
        this.content = content;
    }
}

export class SummaryAndMessages {
    constructor(data) {
        this.summary = this.unpackSummary(data.summary);
        this.messages = this.unpackMessages(data.messages);
    }
    unpackSummary(summaryData) {
        return new Summary(summaryData.id, summaryData.title, summaryData.summary, summaryData.entities);
    }
    unpackMessages(messagesData) {
        return messagesData.map(msg => new Message(msg.id, msg.role, msg.content));
    }
}