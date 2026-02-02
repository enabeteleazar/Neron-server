import { messages, type Message, type InsertMessage } from "@shared/schema";
import { db } from "./db";
import { eq } from "drizzle-orm";

export interface IStorage {
  // Chat
  createMessage(message: InsertMessage): Promise<Message>;
  getMessages(): Promise<Message[]>;
}

export class DatabaseStorage implements IStorage {
  async createMessage(insertMessage: InsertMessage): Promise<Message> {
    const [message] = await db
      .insert(messages)
      .values(insertMessage)
      .returning();
    return message;
  }

  async getMessages(): Promise<Message[]> {
    return await db.select().from(messages);
  }
}

export const storage = new DatabaseStorage();
