import streamlit as st
from mitra import process_files, __description__
from args import Setup

def main():
    st.set_page_config(page_title="Mitra Polyglot Generator", layout="wide")
    st.title("Mitra - Polyglot File Generator")
    st.write("This tool generates polyglot files by combining two input files using various techniques.")

    st.header("Controls")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Upload Files")
        uploaded_file1 = st.file_uploader("Upload the first file (e.g., the container)")
        uploaded_file2 = st.file_uploader("Upload the second file (e.g., the payload)")

    with col2:
        st.subheader("2. Select Options")
        reverse = st.checkbox("Reverse Order (file2 as container)")
        split = st.checkbox("Split Payloads")
        force = st.checkbox("Force File 2 as a generic binary blob")
        overlap = st.checkbox("Generate Overlapping Polyglots (experimental)")
        pad = st.number_input("Pad payloads to a specific size (in Kb)", min_value=0, value=0, step=1)

    st.header("3. Generate")
    generate_button = st.button("Generate Polyglots")

    if generate_button:
        if uploaded_file1 and uploaded_file2:
            file1_name = uploaded_file1.name
            file1_data = uploaded_file1.getvalue()
            file2_name = uploaded_file2.name
            file2_data = uploaded_file2.getvalue()

            options = {
                'file1': file1_name,
                'file2': file2_name,
                'reverse': reverse,
                'split': split,
                'force': force,
                'overlap': overlap,
                'pad': pad,
                'outdir': 'out',
                'splitdir': 'out',
                'nofile': True,
                'verbose': True, # Capture verbose output for the log
            }

            Setup(__description__, config=options)

            with st.spinner("Processing... this may take a moment."):
                results, generated_files = process_files(
                    file1_name, file1_data,
                    file2_name, file2_data
                )

            st.header("Results")

            res_col1, res_col2 = st.columns(2)

            with res_col1:
                st.subheader("Generation Log")
                st.text_area("Log Output", value="\\n".join(results), height=400, help="Detailed log of the generation process.")

            with res_col2:
                st.subheader("Download Files")
                if generated_files:
                    for filename, data in generated_files:
                        st.download_button(
                            label=f"Download {filename}",
                            data=data,
                            file_name=filename,
                            mime="application/octet-stream"
                        )
                else:
                    st.warning("No polyglot files were generated. Check the log for more information.")

        else:
            st.error("Please upload both files to begin.")

if __name__ == "__main__":
    main()