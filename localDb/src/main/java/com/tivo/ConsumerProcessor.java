package com.tivo;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tivo.svcutil.util.TivoEnvelope;
import org.apache.kafka.streams.processor.Processor;
import org.apache.kafka.streams.processor.ProcessorContext;
import org.apache.kafka.streams.processor.PunctuationType;
import org.bson.Document;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.io.*;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.Date;
import java.util.Map;
import java.util.TimeZone;

import static com.tivo.KafkaMongoDocker.bodyDataObjectLogCollection;

public class ConsumerProcessor implements Processor<String, byte[]> {

    private static final Logger gLogger = LoggerFactory.getLogger(ConsumerProcessor.class);
    private ProcessorContext mContext = null;
    static final Duration COMMIT_INTERVAL = Duration.ofSeconds(30);
    int mRecordsProcessed = 0;
    int i = 0;
    int count = 0;

    Long epochSevenDaysAgo = 0L;

    public ConsumerProcessor() {
        //this.fileWriter = new FileWriter("./file_st.txt");
        //this.bufferedWriter = new BufferedWriter(this.fileWriter);
        //logger.debug("{} created and opened", this.fileWriter.toString());
        gLogger.info("Init processor constructor");

        LocalDateTime ldt = LocalDateTime.now();
        ZonedDateTime utcZoned = ldt.atZone(ZoneId.of("UTC"));
        ZonedDateTime utcZonedSevenDaysAgo = utcZoned.minusDays(7);
        epochSevenDaysAgo = utcZonedSevenDaysAgo.toEpochSecond();
    }

    @Override
    public void init(ProcessorContext context) {
        this.mContext = context;
        mContext.schedule(COMMIT_INTERVAL.toMillis(),
            PunctuationType.WALL_CLOCK_TIME, (timestamp) -> {
                try {
                    mContext.commit();
                    gLogger.info("Processed " + mRecordsProcessed +" records\n");
                    mRecordsProcessed = 0;
                } catch (Exception e) {
                    System.out.format("Exception in commiting checkpoint in kafka: {}", e.getMessage());
                }
            });
    }

    @Override
    public void process(String key, byte[] value) {
        if(key == null) {
            gLogger.error("Received null key. Dropping it.");
            return;
        }

        try {
            if(count>1000) {
                count = 0;
            }
            long timestamp = mContext.timestamp();
            long offset = mContext.offset();
            Date date = new Date(timestamp);
            DateFormat format = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
            format.setTimeZone(TimeZone.getTimeZone("Etc/UTC"));
            String formattedDate = format.format(date);

            String bodyId = key;
            if(count==0) {
                gLogger.info("Number of recording and deletion messages is: " + i);
                gLogger.info("offset: {}, timestamp: {}, bodyId:{}\n", offset, formattedDate, bodyId);
            }
            count+=1;
            if(KafkaMongoDocker.bodyIds.contains(bodyId) && (timestamp >= epochSevenDaysAgo)) {

                gLogger.info("Create\n" + i + ":\n" + formattedDate + " UTC\n" + key + "\n" + new String(value, "UTF-8") + "\n\n");
                i += 1;

                TivoEnvelope message = TivoEnvelope.parse(value);
                String payload = message.getPayload();

                Document document = Document.parse(payload);
                //bodyDataObjectLogCollection.insertOne(document);
                gLogger.info("{}", document);
            }
            mRecordsProcessed++;
        } catch (Exception e) {
            System.out.println("Exception parsing message:" + value.toString() + "\n" + e);
            gLogger.info("Exception parsing message:" + value.toString() + "\n" + e);
            e.printStackTrace();
        }
    }

    @Override
    public void punctuate(long timestamp) {

    }

    @Override
    public void close() {
        gLogger.info("Closed");
    }
}
