from picamera2 import Picamera2
import cv2
import serial
import time
import numpy as np

# --- Configuración de Comunicación con Arduino ---
# Asegúrate de que el puerto sea el correcto.
# Puedes verificar los puertos disponibles con: ls /dev/tty*
# Comúnmente es /dev/ttyACM0 para Arduino Uno conectado vía USB.
# Añadido timeout para evitar bloqueos
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2) # Espera a que la conexión serial se establezca

# --- Configuración de Cámara ---
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": 'RGB888', "size": (640, 480)} # Resolución de la cámara
))
picam2.start()

# --- Parámetros de Detección de Línea y Control ---
# Para línea negra sobre fondo blanco (ajusta si tu línea tiene otro color)
LOWER_BLACK = np.array([0, 0, 0])
UPPER_BLACK = np.array([50, 50, 50]) # Puede que necesites ajustar estos para tu línea negra

# Número de filas para detectar la línea y espaciado vertical.
# Más filas y menor espaciado dan más precisión pero pueden aumentar la carga de procesamiento.
NUM_DETECTION_ROWS = 5 # Número de filas para detectar la línea (ajustar según preferencia)
ROW_SPACING = 30     # Espaciado vertical entre cada fila de detección (en píxeles)

# El ROI (Región de Interés) empezará más arriba para capturar más de la línea
ROI_Y_START = int(480 * 0.5) # Comienza al 50% de la altura de la imagen
ROI_Y_END = int(ROI_Y_START + (NUM_DETECTION_ROWS * ROW_SPACING)) # Extiende hasta la última fila

# Asegurarse de que el ROI no exceda los límites de la imagen
if ROI_Y_END > 480:
    ROI_Y_END = 480
    ROI_Y_START = ROI_Y_END - (NUM_DETECTION_ROWS * ROW_SPACING)
    if ROI_Y_START < 0:
        ROI_Y_START = 0
        NUM_DETECTION_ROWS = int((ROI_Y_END - ROI_Y_START) / ROW_SPACING)

# Distancia horizontal de los puntos laterales respecto al centro (para visualización)
POINT_OFFSET = 20

# --- Bucle Principal ---
try:
    while True:
        frame = picam2.capture_array() # Captura la imagen como array RGB
        frame_display = frame.copy()   # Copia para dibujar sobre ella

        # Convertir a escala de grises para umbralizado
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Aplicar ROI al frame gris para el procesamiento
        roi_gray = gray[ROI_Y_START:ROI_Y_END, :]

        # Umbralizado binario: Convierte la línea negra en blanco y el fondo en negro
        # Ajusta el umbral (80) si la detección de la línea no es buena.
        _, thresh = cv2.threshold(roi_gray, 80, 255, cv2.THRESH_BINARY_INV) 

        # Lista para almacenar los centros de línea detectados en cada fila
        detected_line_centers_x = []

        # Iterar a través de las filas de detección
        for i in range(NUM_DETECTION_ROWS):
            # Calcula la posición Y de la fila actual en el frame original
            current_y_in_frame = ROI_Y_START + (i * ROW_SPACING)
            
            # Calcula la posición Y de la fila actual dentro del ROI
            strip_start_y_in_roi = i * ROW_SPACING
            strip_end_y_in_roi = strip_start_y_in_roi + 5 # Consideramos una franja de 5 píxeles de alto

            # Asegurarse de que el strip está dentro de los límites de 'thresh'
            strip_end_y_in_roi = min(strip_end_y_in_roi, thresh.shape[0])
            strip = thresh[strip_start_y_in_roi:strip_end_y_in_roi, :]

            # Encontrar contornos en esta franja
            contours, _ = cv2.findContours(strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Encontrar el contorno más grande en la franja
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Calcular el centroide de este contorno
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    # El centroide está en coordenadas relativas al 'strip',
                    # necesitamos convertirlo a coordenadas del frame completo.
                    line_center_x_in_frame = int(M["m10"] / M["m00"])
                    
                    detected_line_centers_x.append(line_center_x_in_frame)
                    
                    # --- Dibujar los puntos de referencia para esta fila (para visualización) ---
                    # Punto rojo (centro de la línea detectada en esta fila)
                    cv2.circle(frame_display, (line_center_x_in_frame, current_y_in_frame), 5, (0, 0, 255), -1) # Rojo
                    
                    # Puntos verdes (derecha)
                    cv2.circle(frame_display, (line_center_x_in_frame + POINT_OFFSET, current_y_in_frame), 5, (0, 255, 0), -1) # Verde

                    # Puntos azules (izquierda)
                    cv2.circle(frame_display, (line_center_x_in_frame - POINT_OFFSET, current_y_in_frame), 5, (255, 0, 0), -1) # Azul
            
        # --- Cálculo del Error Principal ---
        error = 0
        if detected_line_centers_x:
            # Calcular el promedio de los centros de línea detectados
            average_line_center_x = int(np.mean(detected_line_centers_x))
            
            # Calcular el error respecto al centro de la imagen completa
            image_center_x = int(frame.shape[1] / 2) # Centro horizontal de la imagen
            error = average_line_center_x - image_center_x
            
            # Opcional: Escala el error si el rango es demasiado grande para el Arduino o si Kp es muy pequeño.
            # Por ejemplo, si tu error va de -320 a 320, puedes escalarlo a -100 a 100 dividiendo por 3.2.
            # error_scaled = int(error / 3.2)
            
            # Envía el error al Arduino en el formato "E<valor_error>\n"
            arduino.write(f"E{error}\n".encode())
            
            print(f"Centros detectados: {detected_line_centers_x}, Error Promedio: {error}, Enviado: E{error}")
                
        else:
            # No se encontró línea en ninguna de las filas de detección
            # Envía el comando 'S' al Arduino para que se detenga
            arduino.write(b'S\n') # Envía 'S' y un salto de línea
            print("No se encontró línea. Enviado: S")

        # Dibujar la línea del ROI (opcional, para depuración)
        cv2.line(frame_display, (0, ROI_Y_START), (frame_display.shape[1], ROI_Y_START), (255, 255, 0), 1)
        cv2.line(frame_display, (0, ROI_Y_END), (frame_display.shape[1], ROI_Y_END), (255, 255, 0), 1)

        # Mostrar las imágenes
        cv2.imshow("Line Follower Debug", frame_display)
        # cv2.imshow("Threshold ROI", thresh) # Descomenta para ver la imagen umbralizada del ROI
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Programa detenido por el usuario.")
finally:
    arduino.close()
    cv2.destroyAllWindows()
    picam2.stop()